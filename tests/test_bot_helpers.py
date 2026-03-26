from __future__ import annotations

import asyncio
import shutil
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests.support import cleanup_temp_root, load_bot_module, make_temp_dir


class BotHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = make_temp_dir()
        self.addCleanup(shutil.rmtree, self.tmp_path, ignore_errors=True)
        self.addCleanup(cleanup_temp_root)
        self.bot = load_bot_module(self.tmp_path)

    def test_normalize_trims_and_strips_punctuation(self) -> None:
        self.assertEqual(self.bot.normalize("  Привет, Ёж!  "), "привет еж")

    def test_score_emoji_thresholds(self) -> None:
        cases = [
            (0, 0, "📘"),
            (6, 10, "✨"),
            (9, 10, "🏆"),
        ]
        for score, total, expected in cases:
            with self.subTest(score=score, total=total):
                self.assertEqual(self.bot.score_emoji(score, total), expected)

    def test_extract_topic_request(self) -> None:
        cases = [
            ("Хочу урок про путешествия", "путешествия"),
            ("lesson about shopping", "shopping"),
            ("выбери тему сам", ""),
            ("Просто напоминание", None),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(self.bot.extract_topic_request(text), expected)

    def test_format_help_mentions_rules_command(self) -> None:
        help_text = self.bot.format_help()

        self.assertIn("/rules", help_text)
        self.assertIn("разобрать свою фразу", help_text)

    def test_topic_ready_menu_contains_start_button(self) -> None:
        labels = [[button.text for button in row] for row in self.bot.topic_ready_menu().keyboard]

        self.assertEqual(labels[0], [self.bot.START_TOPIC_LESSON_TEXT])

    def test_make_static_topic_copies_lesson_data(self) -> None:
        lesson = {
            "id": 7,
            "title": "Custom lesson",
            "theory": "Theory",
            "examples": ["Example"],
            "vocabulary": [{"en": "word", "ru": "слово"}],
            "exercises": [{"prompt": "Q", "answers": ["a"], "display_answer": "a", "explanation": "why"}],
        }

        topic = self.bot.make_static_topic(lesson)

        self.assertEqual(topic["id"], "static-7")
        self.assertEqual(topic["source"], "static")
        self.assertEqual(topic["topic_seed"], "custom lesson")
        self.assertEqual(topic["title"], lesson["title"])

    def test_build_lesson_session_shuffles_and_maps_exercises(self) -> None:
        exercises = [
            {"prompt": "P1", "answers": ["a1"], "display_answer": "A1", "explanation": "E1", "skill_key": "s1"},
            {"prompt": "P2", "answers": ["a2"], "display_answer": "A2", "explanation": "E2"},
        ]
        with patch.object(self.bot.random, "sample", side_effect=lambda seq, k: list(seq)):
            session = self.bot.build_lesson_session({"id": "lesson-1", "title": "Title", "exercises": exercises})

        self.assertEqual(session["type"], "lesson_practice")
        self.assertEqual(session["topic_id"], "lesson-1")
        self.assertEqual(session["current_index"], 0)
        self.assertEqual(session["questions"][0]["prompt"], "P1")
        self.assertIsNone(session["questions"][1]["skill_key"])

    def test_build_quiz_session_generates_translation_question(self) -> None:
        words = [{"en": "hello", "ru": "привет"}, {"en": "name", "ru": "имя"}]
        for choice_value in (True, False):
            with self.subTest(choice_value=choice_value):
                with patch.object(self.bot.random, "sample", side_effect=lambda seq, k: list(seq)[:k]):
                    with patch.object(self.bot.random, "choice", return_value=choice_value):
                        session = self.bot.build_quiz_session(words, total_questions=5)

                self.assertEqual(session["type"], "quiz")
                self.assertEqual(len(session["questions"]), 2)
                first_question = session["questions"][0]
                if choice_value:
                    self.assertEqual(first_question["prompt"], "Переведи на русский: hello")
                    self.assertEqual(first_question["answers"], ["привет"])
                else:
                    self.assertEqual(first_question["prompt"], "Переведи на английский: привет")
                    self.assertEqual(first_question["answers"], ["hello"])

    def test_register_answer_updates_totals_and_skill_stats(self) -> None:
        user_state = {
            "stats": {"correct_answers": 0, "wrong_answers": 0},
            "word_stats": {},
        }
        question = {"skill_key": "menu"}

        self.bot.register_answer(user_state, question, True)
        self.bot.register_answer(user_state, question, False)

        self.assertEqual(user_state["stats"], {"correct_answers": 1, "wrong_answers": 1})
        self.assertEqual(user_state["word_stats"]["menu"], {"correct": 1, "wrong": 1})

    def test_merge_learned_words_prefers_latest_spelling(self) -> None:
        user_state = {
            "learned_words": [{"en": "Nice to meet you", "ru": "старый перевод"}],
        }
        topic = {
            "vocabulary": [
                {"en": "nice to meet you", "ru": "приятно познакомиться"},
                {"en": "name", "ru": "имя"},
            ]
        }

        self.bot.merge_learned_words(user_state, topic)

        self.assertEqual(
            user_state["learned_words"],
            [
                {"en": "nice to meet you", "ru": "приятно познакомиться"},
                {"en": "name", "ru": "имя"},
            ],
        )

    def test_remember_topic_updates_history_and_caps_sizes(self) -> None:
        user_state = {
            "completed_lessons": [1],
            "lesson_history": [f"Lesson {index}" for index in range(25)],
            "topic_seeds": [f"seed-{index}" for index in range(35)],
            "learned_words": [],
            "requested_topic": "travel",
        }
        topic = {
            "id": 2,
            "title": "Daily routine",
            "topic_seed": "daily routine",
            "vocabulary": [{"en": "work", "ru": "работать"}],
        }

        self.bot.remember_topic(user_state, topic)

        self.assertEqual(user_state["current_topic"], topic)
        self.assertIsNone(user_state["requested_topic"])
        self.assertEqual(user_state["completed_lessons"], [1, 2])
        self.assertEqual(user_state["lesson_history"], [f"Lesson {index}" for index in range(6, 25)] + ["Daily routine"])
        self.assertEqual(user_state["topic_seeds"], [f"seed-{index}" for index in range(6, 35)] + ["daily routine"])
        self.assertEqual(user_state["learned_words"], [{"en": "work", "ru": "работать"}])

    def test_get_words_for_quiz_uses_learned_words_or_fallback(self) -> None:
        learned_state = {"learned_words": [{"en": "hello", "ru": "привет"}], "completed_lessons": []}
        self.assertEqual(self.bot.get_words_for_quiz(learned_state), [{"en": "hello", "ru": "привет"}])

        completed_state = {"learned_words": [], "completed_lessons": ["static-3"]}
        self.assertEqual(self.bot.get_words_for_quiz(completed_state), self.bot.LESSONS[2]["vocabulary"])

        empty_state = {"learned_words": [], "completed_lessons": []}
        self.assertEqual(self.bot.get_words_for_quiz(empty_state), self.bot.get_lesson(0)["vocabulary"])

    def test_evaluate_quiz_answer_normalizes_input(self) -> None:
        question = {
            "answers": ["nice to meet you"],
            "display_answer": "Nice to meet you.",
            "explanation": "Because",
        }

        result = self.bot.evaluate_quiz_answer(question, "Nice to meet you!")

        self.assertTrue(result["is_correct"])
        self.assertEqual(result["correction"], "Nice to meet you.")

    def test_generate_next_topic_prefers_ai_when_available(self) -> None:
        class FakeTutor:
            available = True

            def __init__(self) -> None:
                self.calls = []

            async def generate_lesson(self, user_state, requested_topic=None):
                self.calls.append((user_state, requested_topic))
                return {"id": "ai-1", "source": "openai"}

        fake_tutor = FakeTutor()
        with patch.object(self.bot, "ai_tutor", fake_tutor):
            user_state = {"lesson_index": 0, "requested_topic": "travel"}
            topic = asyncio.run(self.bot.generate_next_topic(user_state))

        self.assertEqual(topic, {"id": "ai-1", "source": "openai"})
        self.assertEqual(fake_tutor.calls, [(user_state, "travel")])
        self.assertEqual(user_state["lesson_index"], 0)

    def test_generate_next_topic_falls_back_to_static_lesson(self) -> None:
        class FakeTutor:
            available = False

        with patch.object(self.bot, "ai_tutor", FakeTutor()):
            user_state = {"lesson_index": 0, "requested_topic": None}
            topic = asyncio.run(self.bot.generate_next_topic(user_state))

        self.assertEqual(topic["id"], "static-1")
        self.assertEqual(topic["source"], "static")
        self.assertEqual(user_state["lesson_index"], 1)

    def test_lesson_uses_saved_requested_topic_without_reasking(self) -> None:
        self.bot.storage.ensure_user(101, "Egor")
        user_state = self.bot.storage.get_user(101)
        user_state["requested_topic"] = "Насекомые"
        self.bot.storage.update_user(101, user_state)

        calls: list[tuple[str, str | None]] = []

        async def fake_start_next_lesson(update, state) -> None:
            calls.append(("start", state.get("requested_topic")))

        async def fake_ask_lesson_topic(update, state) -> None:
            calls.append(("ask", state.get("requested_topic")))

        update = SimpleNamespace(effective_user=SimpleNamespace(id=101, first_name="Egor"))
        context = SimpleNamespace(args=[])

        with patch.object(self.bot, "start_next_lesson", fake_start_next_lesson):
            with patch.object(self.bot, "ask_lesson_topic", fake_ask_lesson_topic):
                asyncio.run(self.bot.lesson(update, context))

        self.assertEqual(calls, [("start", "Насекомые")])

    def test_start_topic_button_starts_saved_topic(self) -> None:
        self.bot.storage.ensure_user(202, "Egor")
        user_state = self.bot.storage.get_user(202)
        user_state["requested_topic"] = "Насекомые"
        self.bot.storage.update_user(202, user_state)

        calls: list[tuple[str, str | None]] = []

        async def fake_start_next_lesson(update, state) -> None:
            calls.append(("start", state.get("requested_topic")))

        async def fake_reply_text(*args, **kwargs) -> None:
            return None

        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=202, first_name="Egor"),
            message=SimpleNamespace(text=self.bot.START_TOPIC_LESSON_TEXT, reply_text=fake_reply_text),
        )
        context = SimpleNamespace()

        with patch.object(self.bot, "start_next_lesson", fake_start_next_lesson):
            asyncio.run(self.bot.handle_text(update, context))

        self.assertEqual(calls, [("start", "Насекомые")])


if __name__ == "__main__":
    unittest.main()
