from __future__ import annotations

import unittest

from app.content import LESSONS, get_all_words, get_lesson, get_lesson_by_id


class ContentTests(unittest.TestCase):
    def test_get_lesson_returns_expected_lesson(self) -> None:
        lesson = get_lesson(0)

        self.assertEqual(lesson["id"], 1)
        self.assertEqual(lesson["title"], LESSONS[0]["title"])

    def test_get_lesson_by_id_returns_none_for_unknown_id(self) -> None:
        self.assertIsNone(get_lesson_by_id(999))

    def test_get_all_words_flattens_every_lesson_vocabulary(self) -> None:
        words = get_all_words()
        expected_words = [item for lesson in LESSONS for item in lesson["vocabulary"]]

        self.assertEqual(words, expected_words)


if __name__ == "__main__":
    unittest.main()
