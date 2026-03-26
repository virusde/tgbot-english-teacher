from __future__ import annotations

import json
import shutil
import unittest

from tests.support import cleanup_temp_root, make_temp_dir, prepare_storage_module


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = make_temp_dir()
        self.addCleanup(shutil.rmtree, self.tmp_path, ignore_errors=True)
        self.addCleanup(cleanup_temp_root)
        self.storage_mod = prepare_storage_module(self.tmp_path)

    def test_storage_initializes_empty_file(self) -> None:
        storage = self.storage_mod.Storage()

        self.assertTrue(self.storage_mod.DATA_FILE.exists())
        payload = json.loads(self.storage_mod.DATA_FILE.read_text(encoding="utf-8"))
        self.assertEqual(payload, {"users": {}})
        self.assertEqual(storage._default_user_state("Anna")["first_name"], "Anna")

    def test_ensure_user_creates_and_normalizes_legacy_state(self) -> None:
        storage = self.storage_mod.Storage()
        legacy_state = {
            "first_name": "",
            "lesson_index": 3,
            "active_quiz": {
                "questions": [{"prompt": "Q1"}],
                "current_index": 1,
                "score": 1,
            },
        }
        self.storage_mod.DATA_FILE.write_text(
            json.dumps({"users": {"42": legacy_state}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        user_state = storage.ensure_user(42, "Maria")

        self.assertEqual(user_state["first_name"], "Maria")
        self.assertEqual(user_state["lesson_index"], 3)
        self.assertFalse(user_state["awaiting_rules_text"])
        self.assertEqual(
            user_state["active_session"],
            {
                "type": "quiz",
                "questions": [{"prompt": "Q1"}],
                "current_index": 1,
                "score": 1,
                "mistakes": [],
            },
        )
        self.assertNotIn("active_quiz", user_state)

    def test_update_user_persists_payload(self) -> None:
        storage = self.storage_mod.Storage()
        payload = storage._default_user_state("Ira")
        payload["stats"]["correct_answers"] = 7

        storage.update_user(7, payload)

        self.assertEqual(storage.get_user(7)["stats"]["correct_answers"], 7)


if __name__ == "__main__":
    unittest.main()
