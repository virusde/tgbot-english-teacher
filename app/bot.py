from __future__ import annotations

from html import escape
import logging
import os
import random
import re
from typing import Any

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.error import Conflict, NetworkError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    Defaults,
    MessageHandler,
    filters,
)

from app.ai_tutor import OpenAITutor
from app.content import LESSONS, get_all_words, get_lesson
from app.storage import Storage

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

storage = Storage()
ai_tutor = OpenAITutor()

PRACTICE_AGAIN_TEXT = "🔁 Еще практика"
NEXT_LESSON_TEXT = "➡️ Следующий урок"
AUTO_TOPIC_TEXT = "🎲 Выбери тему сам"
CANCEL_TOPIC_TEXT = "❌ Отмена"

MENU = ReplyKeyboardMarkup(
    [
        ["/lesson", "/words"],
        ["/quiz", "/repeat"],
        ["/progress", "/help"],
    ],
    resize_keyboard=True,
)

ACTION_MENU = ReplyKeyboardMarkup(
    [
        [PRACTICE_AGAIN_TEXT, NEXT_LESSON_TEXT],
        ["/progress", "/help"],
    ],
    resize_keyboard=True,
)

TOPIC_MENU = ReplyKeyboardMarkup(
    [
        [AUTO_TOPIC_TEXT, CANCEL_TOPIC_TEXT],
        ["/help"],
    ],
    resize_keyboard=True,
)


def normalize(text: str) -> str:
    lowered = text.strip().lower().replace("ё", "е")
    lowered = re.sub(r"[.,!?;:'\"()]", "", lowered)
    return " ".join(lowered.split())


def esc(value: Any) -> str:
    return escape(str(value))


def score_emoji(score: int, total: int) -> str:
    if total == 0:
        return "📘"
    ratio = score / total
    if ratio >= 0.85:
        return "🏆"
    if ratio >= 0.6:
        return "✨"
    return "💪"


def extract_topic_request(text: str) -> str | None:
    stripped = text.strip()
    lowered = stripped.lower()

    if lowered in {"выбери тему сам", "выбирай сам", "сам выбери тему", "surprise me", "choose yourself"}:
        return ""

    patterns = [
        "хочу урок про ",
        "хочу тему про ",
        "урок про ",
        "тема про ",
        "lesson about ",
        "topic about ",
    ]
    for pattern in patterns:
        if lowered.startswith(pattern):
            topic = stripped[len(pattern):].strip(" .!?:;,")
            return topic or None
    return None


def parse_lesson_args(context: ContextTypes.DEFAULT_TYPE) -> str:
    return " ".join(context.args).strip()


def make_static_topic(lesson: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"static-{lesson['id']}",
        "source": "static",
        "topic_seed": normalize(lesson["title"]),
        "title": lesson["title"],
        "theory": lesson["theory"],
        "examples": lesson["examples"],
        "vocabulary": lesson["vocabulary"],
        "exercises": lesson["exercises"],
    }


def format_topic(topic: dict[str, Any]) -> str:
    words = "\n".join(f"▫️ <b>{esc(item['en'])}</b> — {esc(item['ru'])}" for item in topic["vocabulary"])
    examples = "\n".join(f"• <i>{esc(example)}</i>" for example in topic["examples"])
    source_line = (
        "🤖 <b>AI-урок сгенерирован через OpenAI</b>\n\n"
        if topic.get("source") == "openai"
        else "📚 <b>Тема из встроенного курса</b>\n\n"
    )
    return (
        f"{source_line}"
        f"📘 <b>{esc(topic['title'])}</b>\n\n"
        f"🧠 <b>Коротко о теме</b>\n{esc(topic['theory'])}\n\n"
        f"🗣 <b>Примеры</b>\n{examples}\n\n"
        f"🧩 <b>Слова урока</b>\n{words}\n\n"
        "✨ <i>Сразу после этого я дам практику, чтобы закрепить тему.</i>"
    )


def format_help() -> str:
    ai_line = (
        "✅ <b>OpenAI API подключен</b>\n"
        "Бот может генерировать темы и упражнения через OpenAI.\n\n"
        if ai_tutor.enabled
        else "📚 <b>OpenAI API не настроен</b>\nБот использует встроенные уроки. Добавь <code>OPENAI_API_KEY</code> в <code>.env</code>, чтобы включить OpenAI.\n\n"
    )
    return (
        ai_line
        + "🗺 <b>Команды</b>\n"
        "• <code>/lesson</code> — бот спросит тему или предложит выбрать случайную\n"
        "• <code>/lesson путешествия</code> — сразу урок на нужную тему\n"
        "• <code>/topic &lt;тема&gt;</code> — попросить урок на конкретную тему\n"
        "• <code>/words</code> — слова текущей темы\n"
        "• <code>/quiz</code> — общий тест по изученным словам\n"
        "• <code>/repeat</code> — слова, которые стоит повторить\n"
        "• <code>/progress</code> — ваш прогресс\n"
        "• <code>/help</code> — помощь\n\n"
        "🎯 <b>Как проходит обучение</b>\n"
        "Сначала урок, потом упражнения по теме, затем разбор ошибок и выбор следующего шага.\n\n"
        "💬 <b>Можно просто написать</b>\n"
        "Например: <i>Хочу урок про путешествия</i>.\n"
        "Если ничего не говоришь, тему выбираю сам."
    )


def build_lesson_session(topic: dict[str, Any]) -> dict[str, Any]:
    exercises = random.sample(topic["exercises"], k=len(topic["exercises"]))
    questions = [
        {
            "prompt": exercise["prompt"],
            "answers": exercise["answers"],
            "display_answer": exercise["display_answer"],
            "explanation": exercise["explanation"],
            "skill_key": exercise.get("skill_key"),
        }
        for exercise in exercises
    ]
    return {
        "type": "lesson_practice",
        "topic_id": topic["id"],
        "topic_title": topic["title"],
        "questions": questions,
        "current_index": 0,
        "score": 0,
        "mistakes": [],
    }


def build_quiz_session(words: list[dict[str, str]], total_questions: int = 5) -> dict[str, Any]:
    selected = random.sample(words, k=min(total_questions, len(words)))
    questions: list[dict[str, Any]] = []
    for word in selected:
        if random.choice([True, False]):
            questions.append(
                {
                    "prompt": f"Переведи на русский: {word['en']}",
                    "answers": [word["ru"]],
                    "display_answer": word["ru"],
                    "explanation": f"Слово {word['en']} переводится как {word['ru']}.",
                    "skill_key": word["en"],
                }
            )
        else:
            questions.append(
                {
                    "prompt": f"Переведи на английский: {word['ru']}",
                    "answers": [word["en"]],
                    "display_answer": word["en"],
                    "explanation": f"По-английски это слово пишется как {word['en']}.",
                    "skill_key": word["en"],
                }
            )
    return {
        "type": "quiz",
        "questions": questions,
        "current_index": 0,
        "score": 0,
        "mistakes": [],
    }


def format_session_question(session: dict[str, Any]) -> str:
    index = session["current_index"]
    total = len(session["questions"])
    question = session["questions"][index]
    if session["type"] == "lesson_practice":
        title = "🧠 <b>Практика по теме</b>"
    else:
        title = "🎯 <b>Общий квиз</b>"
    return (
        f"{title}\n"
        f"🔹 <b>Вопрос {index + 1} из {total}</b>\n\n"
        f"{esc(question['prompt'])}\n\n"
        "<i>Ответь одним сообщением.</i>"
    )


def format_lesson_summary(session: dict[str, Any]) -> str:
    total = len(session["questions"])
    score = session["score"]
    mistakes = session["mistakes"]
    summary_emoji = score_emoji(score, total)

    lines = [
        f"{summary_emoji} <b>Практика по теме завершена</b>",
        f"Тема: <b>{esc(session['topic_title'])}</b>",
        f"Результат: <b>{score}/{total}</b>",
    ]

    if not mistakes:
        lines.append("")
        lines.append("✅ <b>Супер!</b> Ошибок не было. Ты хорошо понял тему.")
    else:
        lines.append("")
        lines.append("🛠 <b>Разбор ошибок</b>")
        for index, mistake in enumerate(mistakes, start=1):
            lines.append(
                f"\n<b>{index}. {esc(mistake['prompt'])}</b>\n"
                f"👀 Твой ответ: <code>{esc(mistake['user_answer'])}</code>\n"
                f"✅ Лучше так: <code>{esc(mistake['correct_answer'])}</code>\n"
                f"💡 Почему: {esc(mistake['explanation'])}"
            )

    lines.append("")
    lines.append("👉 <b>Что делаем дальше?</b>")
    lines.append("Можно закрепить тему еще раз или перейти к следующему уроку.")
    return "\n".join(lines)


def format_quiz_summary(session: dict[str, Any]) -> str:
    total = len(session["questions"])
    score = session["score"]
    mistakes = session["mistakes"]
    lines = [
        f"{score_emoji(score, total)} <b>Квиз завершен</b>",
        f"Результат: <b>{score}/{total}</b>",
    ]
    if mistakes:
        lines.append("")
        lines.append("🔍 <b>На что стоит обратить внимание</b>")
        for index, mistake in enumerate(mistakes, start=1):
            lines.append(
                f"\n<b>{index}. {esc(mistake['prompt'])}</b>\n"
                f"👀 Твой ответ: <code>{esc(mistake['user_answer'])}</code>\n"
                f"✅ Правильно: <code>{esc(mistake['correct_answer'])}</code>"
            )
    lines.append("")
    lines.append("🚀 Можешь перейти к <code>/repeat</code> или начать новый <code>/lesson</code>.")
    return "\n".join(lines)


def register_answer(user_state: dict[str, Any], question: dict[str, Any], is_correct: bool) -> None:
    skill_key = question.get("skill_key")
    if is_correct:
        user_state["stats"]["correct_answers"] += 1
    else:
        user_state["stats"]["wrong_answers"] += 1

    if not skill_key:
        return

    word_stats = user_state["word_stats"].setdefault(skill_key, {"correct": 0, "wrong": 0})
    if is_correct:
        word_stats["correct"] += 1
    else:
        word_stats["wrong"] += 1


def merge_learned_words(user_state: dict[str, Any], topic: dict[str, Any]) -> None:
    known = {
        normalize(item["en"]): item
        for item in user_state.get("learned_words", [])
        if item.get("en")
    }
    for item in topic.get("vocabulary", []):
        known[normalize(item["en"])] = item
    user_state["learned_words"] = list(known.values())


def remember_topic(user_state: dict[str, Any], topic: dict[str, Any], clear_requested_topic: bool = True) -> None:
    user_state["current_topic"] = topic
    if clear_requested_topic:
        user_state["requested_topic"] = None
    if topic["id"] not in user_state["completed_lessons"]:
        user_state["completed_lessons"].append(topic["id"])
    history = user_state.setdefault("lesson_history", [])
    history.append(topic["title"])
    user_state["lesson_history"] = history[-20:]
    topic_seed = topic.get("topic_seed")
    if topic_seed:
        seeds = user_state.setdefault("topic_seeds", [])
        seeds.append(topic_seed)
        user_state["topic_seeds"] = seeds[-30:]
    merge_learned_words(user_state, topic)


def get_words_for_quiz(user_state: dict[str, Any]) -> list[dict[str, str]]:
    learned_words = user_state.get("learned_words", [])
    if learned_words:
        return learned_words

    completed_ids = set(user_state["completed_lessons"])
    available_words: list[dict[str, str]] = []
    for lesson_data in LESSONS:
        static_id = f"static-{lesson_data['id']}"
        if static_id in completed_ids:
            available_words.extend(lesson_data["vocabulary"])

    if available_words:
        return available_words
    return get_lesson(0)["vocabulary"]


async def generate_next_topic(user_state: dict[str, Any]) -> dict[str, Any] | None:
    requested_topic = user_state.get("requested_topic")
    if ai_tutor.available:
        topic = await ai_tutor.generate_lesson(user_state, requested_topic=requested_topic)
        if topic:
            return topic

    if user_state["lesson_index"] >= len(LESSONS):
        return None

    lesson = get_lesson(user_state["lesson_index"])
    user_state["lesson_index"] += 1
    return make_static_topic(lesson)


async def send_topic_with_practice(
    update: Update,
    user_state: dict[str, Any],
    topic: dict[str, Any],
    *,
    clear_requested_topic: bool = True,
) -> None:
    remember_topic(user_state, topic, clear_requested_topic=clear_requested_topic)
    session = build_lesson_session(topic)
    user_state["active_session"] = session
    storage.update_user(update.effective_user.id, user_state)

    await update.message.reply_text(format_topic(topic), reply_markup=MENU)
    await update.message.reply_text(
        "🔥 <b>Переходим к практике</b>\nСейчас проверим, как ты понял тему.\n\n"
        + format_session_question(session),
        reply_markup=MENU,
    )


async def start_next_lesson(update: Update, user_state: dict[str, Any]) -> None:
    user_state["awaiting_lesson_topic"] = False
    requested_topic_pending = bool(user_state.get("requested_topic"))
    topic = await generate_next_topic(user_state)
    if not topic:
        await update.message.reply_text(
            "🎉 <b>Встроенные уроки закончились</b>\n"
            "Можно продолжать через <code>/quiz</code> или подключить <code>OPENAI_API_KEY</code> для бесконечных AI-уроков.",
            reply_markup=ACTION_MENU,
        )
        return
    if user_state.get("requested_topic") and topic.get("source") != "openai":
        await update.message.reply_text(
            "📝 <b>Тему я запомнил</b>\n"
            "Но сейчас OpenAI недоступен, поэтому запускаю встроенный урок. "
            "Когда AI снова будет доступен, смогу взять именно твою тему.",
            reply_markup=MENU,
        )
    notice = ai_tutor.get_status_notice()
    if notice and topic.get("source") != "openai":
        await update.message.reply_text(notice, reply_markup=MENU)
    await send_topic_with_practice(
        update,
        user_state,
        topic,
        clear_requested_topic=not (requested_topic_pending and topic.get("source") != "openai"),
    )


async def start_current_lesson_practice(update: Update, user_state: dict[str, Any]) -> None:
    topic = user_state.get("current_topic")
    if not topic:
        await update.message.reply_text(
            "📭 <b>Пока нет активной темы для повторной практики</b>\nНачни с <code>/lesson</code>.",
            reply_markup=MENU,
        )
        return

    session = build_lesson_session(topic)
    user_state["active_session"] = session
    storage.update_user(update.effective_user.id, user_state)
    await update.message.reply_text(
        f"🔁 <b>Еще одна практика</b>\nТема: <b>{esc(topic['title'])}</b>\n\n{format_session_question(session)}",
        reply_markup=MENU,
    )


async def ask_lesson_topic(update: Update, user_state: dict[str, Any]) -> None:
    user_state["awaiting_lesson_topic"] = True
    storage.update_user(update.effective_user.id, user_state)
    await update.message.reply_text(
        "🧭 <b>Какую тему подобрать для следующего урока?</b>\n\n"
        "Напиши тему одним сообщением, например:\n"
        "• <i>путешествия</i>\n"
        "• <i>собеседование</i>\n"
        "• <i>Технический директор / Chief Technology Officer (CTO)</i>\n\n"
        "Или нажми <b>🎲 Выбери тему сам</b>, и я сгенерирую ее сам.",
        reply_markup=TOPIC_MENU,
    )


async def start_lesson_with_requested_topic(
    update: Update,
    user_state: dict[str, Any],
    requested_topic: str | None,
) -> None:
    user_state["requested_topic"] = requested_topic or None
    storage.update_user(update.effective_user.id, user_state)
    await start_next_lesson(update, user_state)


async def evaluate_lesson_answer(
    user_state: dict[str, Any],
    question: dict[str, Any],
    user_answer: str,
) -> dict[str, Any]:
    normalized_user_answer = normalize(user_answer)
    accepted_answers = [normalize(answer) for answer in question["answers"]]
    is_exact_match = normalized_user_answer in accepted_answers

    if is_exact_match:
        return {
            "is_correct": True,
            "feedback": "Верно.",
            "correction": question["display_answer"],
            "explanation": question["explanation"],
        }

    topic = user_state.get("current_topic")
    if ai_tutor.available and topic:
        review = await ai_tutor.review_answer(
            topic=topic,
            question=question,
            user_answer=user_answer,
            normalized_user_answer=normalized_user_answer,
            accepted_answers=accepted_answers,
        )
        if review:
            return review

    return {
        "is_correct": is_exact_match,
        "feedback": "Верно." if is_exact_match else "Не совсем.",
        "correction": question["display_answer"],
        "explanation": question["explanation"],
    }


def evaluate_quiz_answer(question: dict[str, Any], user_answer: str) -> dict[str, Any]:
    normalized_user_answer = normalize(user_answer)
    accepted_answers = [normalize(answer) for answer in question["answers"]]
    is_correct = normalized_user_answer in accepted_answers
    return {
        "is_correct": is_correct,
        "feedback": "Верно." if is_correct else "Пока нет.",
        "correction": question["display_answer"],
        "explanation": question["explanation"],
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    storage.ensure_user(user.id, user.first_name)
    if ai_tutor.enabled:
        mode_line = (
            "✅ <b>OpenAI API подключен</b>\n"
            "Бот может генерировать темы и упражнения через OpenAI.\n\n"
        )
        status_notice = ai_tutor.get_status_notice()
        if status_notice:
            mode_line += f"⚠️ <b>Сейчас временный fallback</b>\n{esc(status_notice)}\n\n"
    else:
        mode_line = (
            "📚 <b>OpenAI API не настроен</b>\n"
            "Сейчас бот работает на встроенных уроках.\n\n"
        )
    await update.message.reply_text(
        (
            f"🌟 <b>Привет, {esc(user.first_name or 'друг')}!</b>\n\n"
            f"{mode_line}"
            "📈 <b>Как мы будем учиться</b>\n"
            "Урок → упражнения по теме → разбор ошибок → выбор следующего шага.\n\n"
            "✨ Напиши <code>/lesson</code>, и я спрошу тему.\n"
            "Или сразу: <code>/lesson путешествия</code>."
        ),
        reply_markup=MENU,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_help(), reply_markup=MENU)


async def lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    storage.ensure_user(user_id, update.effective_user.first_name)
    user_state = storage.get_user(user_id)
    raw_topic = parse_lesson_args(context)
    if raw_topic:
        await start_lesson_with_requested_topic(update, user_state, raw_topic)
        return
    await ask_lesson_topic(update, user_state)


async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    storage.ensure_user(user_id, update.effective_user.first_name)
    user_state = storage.get_user(user_id)

    raw_topic = " ".join(context.args).strip()
    if not raw_topic:
        await update.message.reply_text(
            "🗂 <b>Задай тему урока</b>\n"
            "Например: <code>/topic путешествия</code>\n"
            "Или просто напиши сообщением: <i>Хочу урок про собеседование</i>.",
            reply_markup=MENU,
        )
        return

    if normalize(raw_topic) in {"авто", "сам", "random", "auto"}:
        user_state["requested_topic"] = None
        user_state["awaiting_lesson_topic"] = False
        storage.update_user(user_id, user_state)
        await update.message.reply_text(
            "🎲 <b>Окей, тему снова выбираю сам</b>\nСледующий урок будет без фиксированного запроса.",
            reply_markup=MENU,
        )
        return

    user_state["requested_topic"] = raw_topic
    user_state["awaiting_lesson_topic"] = False
    storage.update_user(user_id, user_state)
    await update.message.reply_text(
        f"📝 <b>Тему запомнил</b>\nСледующий урок будет про <b>{esc(raw_topic)}</b>.",
        reply_markup=MENU,
    )


async def words(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    storage.ensure_user(user_id, update.effective_user.first_name)
    user_state = storage.get_user(user_id)

    topic = user_state.get("current_topic")
    if not topic:
        topic = make_static_topic(get_lesson(0))

    word_lines = "\n".join(f"• {item['en']} — {item['ru']}" for item in topic["vocabulary"])
    await update.message.reply_text(
        f"🧩 <b>Слова по теме</b>\n"
        f"Тема: <b>{esc(topic['title'])}</b>\n\n"
        + "\n".join(f"▫️ <b>{esc(item['en'])}</b> — {esc(item['ru'])}" for item in topic["vocabulary"]),
        reply_markup=MENU,
    )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    storage.ensure_user(user_id, update.effective_user.first_name)
    user_state = storage.get_user(user_id)

    available_words = get_words_for_quiz(user_state)
    session = build_quiz_session(available_words)
    user_state["active_session"] = session
    storage.update_user(user_id, user_state)

    await update.message.reply_text(
        "🎯 <b>Запускаю общий квиз</b>\nПроверим слова из уже изученных тем.\n\n"
        + format_session_question(session),
        reply_markup=MENU,
    )


async def repeat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    storage.ensure_user(user_id, update.effective_user.first_name)
    user_state = storage.get_user(user_id)

    word_stats = user_state["word_stats"]
    if not word_stats:
        await update.message.reply_text(
            "🌿 <b>Пока нет слов на повторение</b>\nПройди <code>/lesson</code> или <code>/quiz</code>, и я соберу слабые места.",
            reply_markup=MENU,
        )
        return

    difficult = sorted(
        word_stats.items(),
        key=lambda item: item[1]["wrong"] - item[1]["correct"],
        reverse=True,
    )
    top_items = [item for item in difficult if item[1]["wrong"] > item[1]["correct"]][:5]
    if not top_items:
        await update.message.reply_text(
            "🏆 <b>Отличный результат</b>\nСлабых слов почти нет. Можно смело идти в <code>/lesson</code>.",
            reply_markup=MENU,
        )
        return

    words_map = {item["en"]: item["ru"] for item in get_all_words()}
    for item in user_state.get("learned_words", []):
        words_map[item["en"]] = item["ru"]

    text = "\n".join(
        f"▫️ <b>{esc(en)}</b> — {esc(words_map.get(en, '?'))} "
        f"<i>(ошибок: {stats['wrong']}, верно: {stats['correct']})</i>"
        for en, stats in top_items
    )
    await update.message.reply_text(
        f"🔁 <b>Слова на повторение</b>\n\n{text}",
        reply_markup=MENU,
    )


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    storage.ensure_user(user_id, update.effective_user.first_name)
    user_state = storage.get_user(user_id)

    correct = user_state["stats"]["correct_answers"]
    wrong = user_state["stats"]["wrong_answers"]
    total = correct + wrong
    accuracy = round((correct / total) * 100) if total else 0
    completed = len(set(user_state["completed_lessons"]))

    if ai_tutor.enabled:
        lesson_line = f"• Пройдено уроков: {completed}"
    else:
        lesson_line = f"• Пройдено уроков: {completed}/{len(LESSONS)}"

    status_notice = ai_tutor.get_status_notice()
    status_line = f"\n• AI-режим: локальный fallback" if status_notice else ""

    await update.message.reply_text(
        (
            "📊 <b>Твой прогресс</b>\n\n"
            f"{lesson_line}\n"
            f"• Правильных ответов: <b>{correct}</b>\n"
            f"• Ошибок: <b>{wrong}</b>\n"
            f"• Точность: <b>{accuracy}%</b>"
            f"{status_line}"
        ),
        reply_markup=MENU,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    storage.ensure_user(user_id, update.effective_user.first_name)
    user_state = storage.get_user(user_id)
    text = update.message.text.strip()
    session = user_state.get("active_session")

    if session and text in {PRACTICE_AGAIN_TEXT, NEXT_LESSON_TEXT}:
        await update.message.reply_text(
            "⏳ <b>Сначала закончим текущие упражнения</b>\nПотом я предложу, что делать дальше.",
            reply_markup=MENU,
        )
        return

    if not session:
        if user_state.get("awaiting_lesson_topic"):
            if text == AUTO_TOPIC_TEXT:
                user_state["awaiting_lesson_topic"] = False
                await start_lesson_with_requested_topic(update, user_state, None)
                return
            if text == CANCEL_TOPIC_TEXT:
                user_state["awaiting_lesson_topic"] = False
                storage.update_user(user_id, user_state)
                await update.message.reply_text(
                    "👌 <b>Окей</b>\nКогда будешь готов, снова напиши <code>/lesson</code>.",
                    reply_markup=MENU,
                )
                return

            topic_request = text.strip()
            user_state["awaiting_lesson_topic"] = False
            await start_lesson_with_requested_topic(update, user_state, topic_request)
            return

        topic_request = extract_topic_request(text)
        if topic_request is not None:
            if topic_request == "":
                user_state["requested_topic"] = None
                user_state["awaiting_lesson_topic"] = False
                storage.update_user(user_id, user_state)
                await update.message.reply_text(
                    "🎲 <b>Договорились</b>\nСледующую тему я выберу сам.",
                    reply_markup=MENU,
                )
                return

            user_state["requested_topic"] = topic_request
            user_state["awaiting_lesson_topic"] = False
            storage.update_user(user_id, user_state)
            await update.message.reply_text(
                f"📝 <b>Отлично</b>\nСледующий урок подготовлю про <b>{esc(topic_request)}</b>.\n"
                "Когда будешь готов, нажми <code>/lesson</code>.",
                reply_markup=MENU,
            )
            return

        if text == PRACTICE_AGAIN_TEXT:
            await start_current_lesson_practice(update, user_state)
            return
        if text == NEXT_LESSON_TEXT:
            await start_next_lesson(update, user_state)
            return

        await update.message.reply_text(
            "✨ <b>Готов продолжать</b>\n"
            "Начни с <code>/lesson</code>, запусти <code>/quiz</code>, "
            "или напиши, на какую тему тебе хочется урок.",
            reply_markup=MENU,
        )
        return

    question = session["questions"][session["current_index"]]
    if session["type"] == "lesson_practice":
        review = await evaluate_lesson_answer(user_state, question, text)
    else:
        review = evaluate_quiz_answer(question, text)

    is_correct = bool(review["is_correct"])
    register_answer(user_state, question, is_correct)
    if is_correct:
        session["score"] += 1
    else:
        session["mistakes"].append(
            {
                "prompt": question["prompt"],
                "user_answer": text,
                "correct_answer": review["correction"],
                "explanation": review["explanation"],
            }
        )

    session["current_index"] += 1
    user_state["active_session"] = session

    if session["current_index"] >= len(session["questions"]):
        user_state["active_session"] = None
        storage.update_user(user_id, user_state)

        if session["type"] == "lesson_practice":
            await update.message.reply_text(
                format_lesson_summary(session),
                reply_markup=ACTION_MENU,
            )
        else:
            await update.message.reply_text(
                format_quiz_summary(session),
                reply_markup=MENU,
            )
        return

    storage.update_user(user_id, user_state)

    if is_correct:
        feedback_line = f"✅ <b>{esc(review['feedback'])}</b>"
    else:
        feedback_line = (
            f"🛠 <b>{esc(review['feedback'])}</b>\n"
            f"✅ Лучше так: <code>{esc(review['correction'])}</code>\n"
            f"💡 Почему: {esc(review['explanation'])}"
        )

    next_prompt = format_session_question(session)
    await update.message.reply_text(
        f"{feedback_line}\n\n{next_prompt}",
        reply_markup=MENU,
    )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    if isinstance(error, Conflict):
        logging.getLogger(__name__).warning(
            "Another bot instance is already using getUpdates. Stop the old process before starting a new one."
        )
        return
    if isinstance(error, NetworkError) and "RemoteProtocolError" in str(error):
        logging.getLogger(__name__).warning(
            "Telegram polling connection was interrupted. The library will retry automatically."
        )
        return

    logging.getLogger(__name__).exception("Unhandled bot error", exc_info=error)


def run() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не найден BOT_TOKEN. Создайте .env на основе .env.example")

    application = (
        Application.builder()
        .token(token)
        .defaults(Defaults(parse_mode="HTML"))
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .connection_pool_size(8)
        .pool_timeout(10)
        .connect_timeout(10)
        .read_timeout(20)
        .write_timeout(20)
        .get_updates_connection_pool_size(2)
        .get_updates_pool_timeout(15)
        .get_updates_connect_timeout(15)
        .get_updates_read_timeout(30)
        .get_updates_write_timeout(15)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lesson", lesson))
    application.add_handler(CommandHandler("topic", topic_command))
    application.add_handler(CommandHandler("words", words))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("repeat", repeat))
    application.add_handler(CommandHandler("progress", progress))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(handle_error)

    application.run_polling(allowed_updates=Update.ALL_TYPES)
