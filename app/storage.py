from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE = DATA_DIR / "progress.json"


class Storage:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not DATA_FILE.exists():
            DATA_FILE.write_text(json.dumps({"users": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _default_user_state(self, first_name: str | None = None) -> dict[str, Any]:
        return {
            "first_name": first_name or "",
            "lesson_index": 0,
            "current_lesson_id": None,
            "current_topic": None,
            "requested_topic": None,
            "awaiting_lesson_topic": False,
            "completed_lessons": [],
            "lesson_history": [],
            "topic_seeds": [],
            "learned_words": [],
            "stats": {
                "correct_answers": 0,
                "wrong_answers": 0,
            },
            "word_stats": {},
            "active_session": None,
        }

    def _normalize_user_state(self, user_state: dict[str, Any], first_name: str | None = None) -> dict[str, Any]:
        normalized = self._default_user_state(first_name)
        normalized.update(user_state)

        if first_name and not normalized["first_name"]:
            normalized["first_name"] = first_name

        if "active_quiz" in user_state and not normalized.get("active_session"):
            active_quiz = user_state.get("active_quiz")
            if active_quiz:
                normalized["active_session"] = {
                    "type": "quiz",
                    "questions": active_quiz.get("questions", []),
                    "current_index": active_quiz.get("current_index", 0),
                    "score": active_quiz.get("score", 0),
                    "mistakes": [],
                }
        normalized.pop("active_quiz", None)
        return normalized

    def _read(self) -> dict[str, Any]:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_user(self, user_id: int, first_name: str | None = None) -> dict[str, Any]:
        data = self._read()
        key = str(user_id)
        if key not in data["users"]:
            data["users"][key] = self._default_user_state(first_name)
            self._write(data)
            return data["users"][key]

        normalized = self._normalize_user_state(data["users"][key], first_name)
        if normalized != data["users"][key]:
            data["users"][key] = normalized
            self._write(data)
        return normalized

    def get_user(self, user_id: int) -> dict[str, Any]:
        data = self._read()
        key = str(user_id)
        user_state = self._normalize_user_state(data["users"][key])
        if user_state != data["users"][key]:
            data["users"][key] = user_state
            self._write(data)
        return user_state

    def update_user(self, user_id: int, user_state: dict[str, Any]) -> None:
        data = self._read()
        data["users"][str(user_id)] = self._normalize_user_state(user_state)
        self._write(data)
