from __future__ import annotations

import re
from typing import Any

QUESTION_WORDS = {"what", "where", "when", "why", "how", "who", "which", "whose", "whom"}
QUESTION_AUXILIARIES = {
    "am",
    "is",
    "are",
    "do",
    "does",
    "did",
    "can",
    "could",
    "will",
    "would",
    "should",
    "have",
    "has",
    "had",
}
COMMON_BASE_VERBS = {
    "go",
    "work",
    "study",
    "play",
    "read",
    "watch",
    "visit",
    "live",
    "like",
    "want",
    "need",
    "speak",
    "drink",
    "eat",
    "learn",
}
THIRD_PERSON_FORMS = {
    "go": "goes",
    "work": "works",
    "study": "studies",
    "play": "plays",
    "read": "reads",
    "watch": "watches",
    "visit": "visits",
    "live": "lives",
    "like": "likes",
    "want": "wants",
    "need": "needs",
    "speak": "speaks",
    "drink": "drinks",
    "eat": "eats",
    "learn": "learns",
}
BASE_FROM_THIRD_PERSON = {value: key for key, value in THIRD_PERSON_FORMS.items()}
IRREGULAR_PAST = {
    "go": "went",
    "eat": "ate",
    "see": "saw",
    "do": "did",
    "have": "had",
}
PAST_MARKERS = ("yesterday", "last night", "last week", "last month", "last year")
FUTURE_MARKERS = ("tomorrow", "next week", "next month", "next year")


def clean_spacing(text: str) -> str:
    return " ".join(text.strip().split())


def is_probable_question(text: str) -> bool:
    cleaned = clean_spacing(text)
    if not cleaned:
        return False
    if cleaned.endswith("?"):
        return True
    first_word = re.sub(r"[^a-z']", "", cleaned.split()[0].lower())
    return first_word in QUESTION_WORDS or first_word in QUESTION_AUXILIARIES


def format_english_sentence(text: str) -> str:
    cleaned = clean_spacing(text)
    if not cleaned:
        return ""

    cleaned = re.sub(r"\bi\b", "I", cleaned, flags=re.IGNORECASE)
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    if cleaned[-1] not in ".!?":
        cleaned += "?" if is_probable_question(cleaned) else "."
    return cleaned


def analyze_text_locally(text: str) -> dict[str, Any]:
    original_text = clean_spacing(text)
    working = original_text
    issues: list[dict[str, str]] = []

    if not original_text:
        return {
            "source": "local",
            "is_correct": False,
            "original_text": "",
            "corrected_text": "",
            "summary": "Пришли одну английскую фразу или вопрос, и я разберу их по шагам.",
            "issues": [],
            "rule_notes": [],
        }

    question_corrected = _fix_question_word_order(working)
    if question_corrected != working:
        working = question_corrected
        issues.append(
            {
                "title": "Порядок слов в вопросе",
                "details": "В английском вопросе обычно нужен вспомогательный глагол перед подлежащим.",
                "rule": "Схема: question word + do/does + subject + verb.",
            }
        )

    working, changed = _replace_patterns(
        working,
        [
            (r"\bi\s+(?:is|are)\b", "I am"),
            (r"\b(you|we|they)\s+(?:is|am)\b", r"\1 are"),
            (r"\b(he|she|it)\s+(?:am|are)\b", r"\1 is"),
        ],
    )
    if changed:
        issues.append(
            {
                "title": "Форма глагола to be",
                "details": "Форма to be зависит от подлежащего: I am, you/we/they are, he/she/it is.",
                "rule": "Подбирай am / is / are под местоимение, а не одну форму для всех случаев.",
            }
        )

    working, changed = _replace_patterns(
        working,
        [
            (r"\b(he|she|it)\s+don't\b", r"\1 doesn't"),
            (r"\b(i|you|we|they)\s+doesn't\b", r"\1 don't"),
        ],
    )
    if changed:
        issues.append(
            {
                "title": "Don't / doesn't",
                "details": "В Present Simple после he / she / it используется doesn't, а не don't.",
                "rule": "He doesn't, she doesn't, it doesn't; I/you/we/they don't.",
            }
        )

    continuous_corrected = _fix_present_continuous(working)
    if continuous_corrected != working:
        working = continuous_corrected
        issues.append(
            {
                "title": "Форма Present Continuous",
                "details": "После am / is / are в длительном времени нужен глагол с окончанием -ing.",
                "rule": "Схема: subject + am/is/are + verb-ing.",
            }
        )

    present_simple_corrected = _fix_present_simple_agreement(working)
    if present_simple_corrected != working:
        working = present_simple_corrected
        issues.append(
            {
                "title": "Согласование сказуемого",
                "details": "В Present Simple после he / she / it смысловой глагол обычно получает окончание -s / -es.",
                "rule": "He works, she lives, it goes; но I work, you live, they go.",
            }
        )

    tense_corrected = _fix_obvious_time_marker_mismatch(working)
    if tense_corrected != working:
        working = tense_corrected
        issues.append(
            {
                "title": "Подсказка по времени",
                "details": "Маркер времени и форма глагола должны совпадать по смыслу.",
                "rule": "Yesterday обычно тянет Past Simple, а tomorrow часто требует future form.",
            }
        )

    corrected_text = format_english_sentence(working)
    formatted_original = format_english_sentence(original_text)
    if corrected_text == formatted_original and original_text != corrected_text:
        issues.append(
            {
                "title": "Оформление фразы",
                "details": "Я поправил только запись: заглавную букву, пробелы или конечный знак.",
                "rule": "Предложение лучше начинать с заглавной буквы и заканчивать точкой или вопросительным знаком.",
            }
        )

    is_correct = corrected_text == formatted_original and len(issues) <= 1 and (
        not issues or issues[0]["title"] == "Оформление фразы"
    )
    summary = (
        "Фраза выглядит грамотно. Ниже оставил короткое правило, чтобы конструкция легче запомнилась."
        if is_correct
        else "Я поправил фразу и отметил ключевые места, на которые стоит смотреть в похожих предложениях."
    )

    return {
        "source": "local",
        "is_correct": is_correct,
        "original_text": original_text,
        "corrected_text": corrected_text,
        "summary": summary,
        "issues": issues,
        "rule_notes": infer_rule_notes(corrected_text),
    }


def infer_rule_notes(text: str) -> list[str]:
    lowered = clean_spacing(text).lower()
    notes: list[str] = []

    if not lowered:
        return notes

    if is_probable_question(lowered):
        notes.append("В вопросах важен порядок слов: сначала вопросительное слово или вспомогательный глагол, потом подлежащее.")
    if re.search(r"\b(am|is|are)\s+\w+ing\b", lowered):
        notes.append("Конструкция am / is / are + verb-ing показывает действие в процессе: Present Continuous.")
    elif re.search(r"\b(will|going to)\b", lowered):
        notes.append("Формы will и going to помогают говорить о будущем: планах, прогнозах и решениях.")
    elif any(marker in lowered for marker in PAST_MARKERS):
        notes.append("Слова вроде yesterday и last week обычно подсказывают Past Simple.")
    else:
        notes.append("Для обычных фактов и привычек чаще всего используется Present Simple.")

    return notes[:2]


def _replace_patterns(text: str, patterns: list[tuple[str, str]]) -> tuple[str, bool]:
    updated = text
    changed = False
    for pattern, replacement in patterns:
        updated, count = re.subn(pattern, replacement, updated, flags=re.IGNORECASE)
        changed = changed or count > 0
    return updated, changed


def _fix_question_word_order(text: str) -> str:
    match = re.match(
        r"^\s*(where|what|when|why|how)\s+(i|you|we|they|he|she|it)\s+([a-z']+)(.*)$",
        clean_spacing(text),
        flags=re.IGNORECASE,
    )
    if not match:
        return text

    question_word, subject, verb, tail = match.groups()
    lower_subject = subject.lower()
    aux = "does" if lower_subject in {"he", "she", "it"} else "do"
    base_verb = BASE_FROM_THIRD_PERSON.get(verb.lower(), verb.lower())
    tail = tail.rstrip("?.! ")
    return f"{question_word.lower()} {aux} {lower_subject} {base_verb}{tail}"


def _fix_present_continuous(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        be_verb = match.group(1)
        base_verb = match.group(2).lower()
        return f"{be_verb} {_to_ing_form(base_verb)}"

    return re.sub(
        r"\b(am|is|are)\s+(go|work|study|play|read|watch|visit|live|speak|learn)\b",
        repl,
        text,
        flags=re.IGNORECASE,
    )


def _fix_present_simple_agreement(text: str) -> str:
    updated = text

    def third_person_repl(match: re.Match[str]) -> str:
        subject = match.group(1)
        verb = match.group(2).lower()
        return f"{subject} {THIRD_PERSON_FORMS[verb]}"

    updated = re.sub(
        r"\b(he|she|it)\s+(go|work|study|play|read|watch|visit|live|like|want|need|speak|drink|eat|learn)\b",
        third_person_repl,
        updated,
        flags=re.IGNORECASE,
    )

    def plural_repl(match: re.Match[str]) -> str:
        subject = match.group(1)
        verb = match.group(2).lower()
        return f"{subject} {BASE_FROM_THIRD_PERSON[verb]}"

    updated = re.sub(
        r"\b(i|you|we|they)\s+(goes|works|studies|plays|reads|watches|visits|lives|likes|wants|needs|speaks|drinks|eats|learns)\b",
        plural_repl,
        updated,
        flags=re.IGNORECASE,
    )
    return updated


def _fix_obvious_time_marker_mismatch(text: str) -> str:
    lowered = clean_spacing(text).lower()

    if any(marker in lowered for marker in PAST_MARKERS):
        return re.sub(
            r"\b(i|you|we|they|he|she|it)\s+(go|eat|see|do|have)\b",
            lambda match: f"{match.group(1)} {IRREGULAR_PAST[match.group(2).lower()]}",
            text,
            count=1,
            flags=re.IGNORECASE,
        )

    if any(marker in lowered for marker in FUTURE_MARKERS):
        return re.sub(
            r"\b(i|you|we|they|he|she|it)\s+(went|ate|saw|did|had)\b",
            lambda match: f"{match.group(1)} will {_base_from_past(match.group(2).lower())}",
            text,
            count=1,
            flags=re.IGNORECASE,
        )

    return text


def _to_ing_form(verb: str) -> str:
    if verb.endswith("ie"):
        return verb[:-2] + "ying"
    if verb.endswith("e") and verb not in {"be", "see"}:
        return verb[:-1] + "ing"
    if verb.endswith("y"):
        return verb[:-1] + "ying"
    return verb + "ing"


def _base_from_past(past_form: str) -> str:
    for base, past in IRREGULAR_PAST.items():
        if past == past_form:
            return base
    return past_form
