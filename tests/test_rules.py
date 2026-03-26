from __future__ import annotations

import unittest

from app.rules import analyze_text_locally, format_english_sentence, is_probable_question


class RulesTests(unittest.TestCase):
    def test_is_probable_question_detects_question_words(self) -> None:
        self.assertTrue(is_probable_question("Where you live"))
        self.assertFalse(is_probable_question("I live in Moscow"))

    def test_format_english_sentence_normalizes_case_and_punctuation(self) -> None:
        self.assertEqual(format_english_sentence("i live in moscow"), "I live in moscow.")
        self.assertEqual(format_english_sentence("where do you live"), "Where do you live?")

    def test_local_rules_review_fixes_question_word_order(self) -> None:
        review = analyze_text_locally("Where you live")

        self.assertEqual(review["corrected_text"], "Where do you live?")
        self.assertFalse(review["is_correct"])
        self.assertTrue(any(issue["title"] == "Порядок слов в вопросе" for issue in review["issues"]))

    def test_local_rules_review_fixes_present_simple_agreement(self) -> None:
        review = analyze_text_locally("He go to school")

        self.assertEqual(review["corrected_text"], "He goes to school.")
        self.assertTrue(any(issue["title"] == "Согласование сказуемого" for issue in review["issues"]))

    def test_local_rules_review_fixes_negative_form(self) -> None:
        review = analyze_text_locally("She don't like coffee")

        self.assertEqual(review["corrected_text"], "She doesn't like coffee.")
        self.assertTrue(any(issue["title"] == "Don't / doesn't" for issue in review["issues"]))

    def test_local_rules_review_recognizes_correct_sentence(self) -> None:
        review = analyze_text_locally("I am reading now.")

        self.assertTrue(review["is_correct"])
        self.assertEqual(review["corrected_text"], "I am reading now.")
        self.assertGreaterEqual(len(review["rule_notes"]), 1)


if __name__ == "__main__":
    unittest.main()
