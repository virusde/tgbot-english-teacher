from __future__ import annotations

import json
import unittest
import shutil

from tests.support import make_temp_dir, prepare_storage_module


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp_path = make_temp_dir()
        self.addCleanup(shutil.rmtree, self.tmp_path, ignore_errors=True)
        self.storage_mod = prepare_storage_module(self.tmp_path)

    def test_storage_initializes_empty_file(self):
        storage = self.storage_mod.Storage()

        self.assertTrue(self.storage_mod.DATA_FILE.exists())
        payload = json.loads(self.storage_mod.DATA_FILE.read_text(encoding="utf-8"))
        self.assertEqual(payload, {"users": {}})
        self.assertEqual(storage._default_user_state("Anna")["first_name"], "Anna")

    def test_ensure_user_creates_and_normalizes_legacy_state(self):
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

    def test_update_user_persists_payload(self):
        storage = self.storage_mod.Storage()
        payload = storage._default_user_state("Ira")
        payload["stats"]["correct_answers"] = 7

        storage.update_user(7, payload)

        self.assertEqual(storage.get_user(7)["stats"]["correct_answers"], 7)


if __name__ == "__main__":
    unittest.main()
