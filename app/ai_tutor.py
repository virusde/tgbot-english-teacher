from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RESPONSES_URL = "https://api.openai.com/v1/responses"
TOPIC_SEED_POOL = [
    "shopping",
    "doctor visit",
    "job interview",
    "airport check-in",
    "hotel stay",
    "friendship and small talk",
    "movies and series",
    "music",
    "fitness",
    "healthy habits",
    "cafe and ordering",
    "phone calls",
    "online meetings",
    "office communication",
    "studying and exams",
    "home and apartment",
    "repairs and problems",
    "banking and payments",
    "documents and forms",
    "weekend plans",
    "city directions",
    "public transport",
    "weather and clothes",
    "technology and gadgets",
    "social media",
    "family life",
    "pets",
    "holiday planning",
    "customer support",
    "emotions and feelings",
]


class OpenAITutor:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.lesson_model = os.getenv("OPENAI_LESSON_MODEL") or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.review_model = os.getenv("OPENAI_REVIEW_MODEL", "gpt-5-nano")
        self.timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))
        self.cooldown_until = 0.0
        self.last_error_message = ""
        self.last_error_kind = ""

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def available(self) -> bool:
        return self.enabled and time.time() >= self.cooldown_until

    def get_status_notice(self) -> str | None:
        if not self.enabled:
            return None
        if self.available:
            return None

        remaining = max(int(self.cooldown_until - time.time()), 0)
        if self.last_error_kind == "insufficient_quota":
            return (
                "OpenAI сейчас недоступен из-за лимита проекта или квоты, "
                "поэтому я временно работаю на встроенных уроках и локальной проверке."
            )
        if remaining > 0:
            return (
                f"OpenAI временно уперся в rate limit, поэтому ближайшие {remaining} сек. "
                "я работаю в локальном режиме без запросов к API."
            )
        return "OpenAI временно недоступен, поэтому я работаю в локальном режиме."

    async def generate_lesson(
        self,
        user_state: dict[str, Any],
        requested_topic: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.available:
            return None

        weak_skills = self._weak_skills(user_state)
        lesson_count = len(user_state.get("completed_lessons", []))
        history = user_state.get("lesson_history", [])[-5:]
        recent_topic_seeds = user_state.get("topic_seeds", [])[-8:]
        available_seeds = [seed for seed in TOPIC_SEED_POOL if seed not in recent_topic_seeds]
        if not available_seeds:
            available_seeds = TOPIC_SEED_POOL[:]

        prompt = {
            "student_name": user_state.get("first_name") or "student",
            "lesson_number": lesson_count + 1,
            "previous_topics": history,
            "recent_topic_seeds": recent_topic_seeds,
            "available_topic_seeds": available_seeds,
            "requested_topic": requested_topic or "",
            "weak_skills": weak_skills,
            "requirements": [
                "Create a short English lesson for a Russian-speaking learner.",
                "Target CEFR level A1-A2.",
                "Theory must be in Russian.",
                "Examples and correct answers must be in English.",
                "Return exactly 4 examples, 5 vocabulary items, and 3 exercises.",
                "Choose a practical everyday topic and avoid repeating previous topics when possible.",
                "Exercises must check understanding of the lesson topic, not random vocabulary only.",
                "Accepted answers should include 1 to 3 short valid variants.",
                "If requested_topic is provided, make the lesson clearly centered on it.",
                "If requested_topic is empty, choose a topic_seed from available_topic_seeds and avoid the recent_topic_seeds.",
                "Do not create a near-duplicate of previous_topics even with different wording.",
                "Prefer concrete situations over vague topics.",
            ],
        }

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "topic_seed": {"type": "string"},
                "theory": {"type": "string"},
                "examples": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "vocabulary": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "en": {"type": "string"},
                            "ru": {"type": "string"},
                        },
                        "required": ["en", "ru"],
                        "additionalProperties": False,
                    },
                },
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "answers": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "display_answer": {"type": "string"},
                            "explanation": {"type": "string"},
                            "skill_key": {"type": "string"},
                        },
                        "required": ["prompt", "answers", "display_answer", "explanation", "skill_key"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "topic_seed", "theory", "examples", "vocabulary", "exercises"],
            "additionalProperties": False,
        }

        try:
            lesson = await self._request_json(
                model=self.lesson_model,
                system_prompt=(
                    "You are an English tutor creating compact, practical lessons for a Telegram bot. "
                    "Always return valid JSON that matches the schema."
                ),
                user_payload=prompt,
                schema_name="lesson_plan",
                schema=schema,
            )
        except Exception as exc:
            logger.warning("OpenAI lesson generation failed: %s", self._format_exception(exc))
            return None

        lesson["id"] = f"ai-{lesson_count + 1}"
        lesson["source"] = "openai"
        lesson["topic_seed"] = lesson["topic_seed"].strip().lower()
        return lesson

    async def review_answer(
        self,
        topic: dict[str, Any],
        question: dict[str, Any],
        user_answer: str,
        normalized_user_answer: str,
        accepted_answers: list[str],
    ) -> dict[str, Any] | None:
        if not self.available:
            return None

        payload = {
            "topic_title": topic.get("title"),
            "topic_theory": topic.get("theory"),
            "question": question.get("prompt"),
            "accepted_answers": question.get("answers"),
            "student_answer": user_answer,
            "student_answer_normalized": normalized_user_answer,
            "grading_rules": [
                "Be tolerant to punctuation and letter case.",
                "Minor spelling issues are acceptable only if the meaning is still clearly correct.",
                "Accept short equivalent phrasings if they answer the same exercise target.",
                "Do not accept answers that change the grammar target or core meaning.",
                "Explain the result in Russian briefly and supportively.",
            ],
        }

        schema = {
            "type": "object",
            "properties": {
                "is_correct": {"type": "boolean"},
                "feedback": {"type": "string"},
                "correction": {"type": "string"},
                "explanation": {"type": "string"},
            },
            "required": ["is_correct", "feedback", "correction", "explanation"],
            "additionalProperties": False,
        }

        try:
            review = await self._request_json(
                model=self.review_model,
                system_prompt=(
                    "You evaluate English-learning answers for a Telegram tutor bot. "
                    "Be fair, concise, and return valid JSON only."
                ),
                user_payload=payload,
                schema_name="answer_review",
                schema=schema,
            )
        except Exception as exc:
            logger.warning("OpenAI answer review failed: %s", self._format_exception(exc))
            return None

        review["accepted_answers"] = accepted_answers
        return review

    async def explain_sentence(self, text: str) -> dict[str, Any] | None:
        if not self.available:
            return None

        payload = {
            "student_text": text,
            "requirements": [
                "Detect whether the English sentence or question is natural and grammatically correct.",
                "If needed, provide one corrected version in English.",
                "Explain the issues in Russian in a supportive teaching tone.",
                "Focus on word order, tense, articles, prepositions, auxiliary verbs, and word choice when relevant.",
                "Return concise practical guidance for a beginner learner.",
                "If the sentence is already acceptable, keep corrected_text the same and explain what is used correctly.",
            ],
        }

        schema = {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "is_correct": {"type": "boolean"},
                "original_text": {"type": "string"},
                "corrected_text": {"type": "string"},
                "summary": {"type": "string"},
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "details": {"type": "string"},
                            "rule": {"type": "string"},
                        },
                        "required": ["title", "details", "rule"],
                        "additionalProperties": False,
                    },
                },
                "rule_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "source",
                "is_correct",
                "original_text",
                "corrected_text",
                "summary",
                "issues",
                "rule_notes",
            ],
            "additionalProperties": False,
        }

        try:
            review = await self._request_json(
                model=self.review_model,
                system_prompt=(
                    "You analyze short English learner sentences for a Telegram tutor bot. "
                    "Return valid JSON only. All explanations, titles, rules, and summaries must be in Russian. "
                    "The corrected sentence must be in English."
                ),
                user_payload=payload,
                schema_name="sentence_review",
                schema=schema,
            )
        except Exception as exc:
            logger.warning("OpenAI sentence review failed: %s", self._format_exception(exc))
            return None

        review["source"] = "openai"
        return review

    async def _request_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(2):
                try:
                    response = await client.post(
                        RESPONSES_URL,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "instructions": system_prompt,
                            "input": json.dumps(user_payload, ensure_ascii=False),
                            "text": {
                            "format": {
                                "type": "json_schema",
                                "name": schema_name,
                                "schema": schema,
                                "strict": True,
                            }
                            },
                        },
                    )
                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError as exc:
                    self._handle_http_error(exc)
                    raise
                except httpx.TimeoutException as exc:
                    self.last_error_kind = "timeout"
                    self.last_error_message = self._format_exception(exc)
                    if attempt == 0:
                        await asyncio.sleep(1)
                        continue
                    self.cooldown_until = time.time() + 30
                    raise
                except httpx.TransportError as exc:
                    self.last_error_kind = "transport_error"
                    self.last_error_message = self._format_exception(exc)
                    self.cooldown_until = time.time() + 30
                    raise

        response_json = response.json()
        text = self._extract_output_text(response_json)
        if not text:
            raise RuntimeError("Empty response from OpenAI")
        return json.loads(text)

    def _extract_output_text(self, response_json: dict[str, Any]) -> str:
        texts: list[str] = []
        for item in response_json.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    texts.append(content["text"])
        return "".join(texts).strip()

    def _weak_skills(self, user_state: dict[str, Any]) -> list[str]:
        difficult = []
        for skill, stats in user_state.get("word_stats", {}).items():
            balance = stats.get("wrong", 0) - stats.get("correct", 0)
            if balance > 0:
                difficult.append((balance, skill))
        difficult.sort(reverse=True)
        return [skill for _, skill in difficult[:5]]

    def _handle_http_error(self, exc: httpx.HTTPStatusError) -> None:
        response = exc.response
        if response.status_code != 429:
            self.last_error_kind = "http_error"
            self.last_error_message = f"HTTP {response.status_code}"
            return

        retry_after_header = response.headers.get("retry-after")
        retry_after_seconds = self._safe_retry_after_seconds(retry_after_header)
        error_kind = "rate_limit"
        error_message = "Rate limit exceeded"

        try:
            payload = response.json()
            error = payload.get("error", {})
            error_kind = error.get("code") or error.get("type") or error_kind
            error_message = error.get("message") or error_message
        except ValueError:
            pass

        if error_kind == "insufficient_quota":
            retry_after_seconds = max(retry_after_seconds, 900)

        self.cooldown_until = time.time() + retry_after_seconds
        self.last_error_kind = error_kind
        self.last_error_message = error_message
        logger.warning(
            "OpenAI API 429 received (%s). Cooling down for %s seconds.",
            error_kind,
            retry_after_seconds,
        )

    def _safe_retry_after_seconds(self, retry_after_header: str | None) -> int:
        if not retry_after_header:
            return 90
        try:
            value = int(float(retry_after_header))
        except ValueError:
            return 90
        return max(value, 30)

    def _format_exception(self, exc: Exception) -> str:
        detail = str(exc).strip()
        if detail:
            return f"{exc.__class__.__name__}: {detail}"
        if self.last_error_message:
            return f"{exc.__class__.__name__}: {self.last_error_message}"
        return exc.__class__.__name__
