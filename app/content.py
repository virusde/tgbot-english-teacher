from __future__ import annotations

LESSONS = [
    {
        "id": 1,
        "title": "Hello and introductions",
        "theory": (
            "Базовые приветствия в английском: hello, hi, good morning, nice to meet you. "
            "Для простого рассказа о себе полезны конструкции I am..., My name is..., I live in..."
        ),
        "examples": [
            "Hello! My name is Anna.",
            "Hi! I am a student.",
            "Nice to meet you.",
            "I live in Moscow.",
        ],
        "vocabulary": [
            {"en": "hello", "ru": "привет"},
            {"en": "name", "ru": "имя"},
            {"en": "student", "ru": "студент"},
            {"en": "live", "ru": "жить"},
            {"en": "nice to meet you", "ru": "приятно познакомиться"},
        ],
        "exercises": [
            {
                "prompt": "Переведи на английский: Привет! Меня зовут Анна.",
                "answers": ["hello! my name is anna.", "hello, my name is anna.", "hello my name is anna"],
                "display_answer": "Hello! My name is Anna.",
                "explanation": "Для представления о себе удобно использовать конструкцию My name is ...",
                "skill_key": "name",
            },
            {
                "prompt": "Заполни пропуск одним словом: I ___ in Moscow.",
                "answers": ["live"],
                "display_answer": "live",
                "explanation": "После I используем базовую форму глагола: I live.",
                "skill_key": "live",
            },
            {
                "prompt": "Как по-английски сказать: Приятно познакомиться?",
                "answers": ["nice to meet you"],
                "display_answer": "Nice to meet you.",
                "explanation": "Это стандартная вежливая фраза при знакомстве.",
                "skill_key": "nice to meet you",
            },
        ],
    },
    {
        "id": 2,
        "title": "Daily routine",
        "theory": (
            "Чтобы говорить о рутине, используйте Present Simple: I work, you study, we sleep. "
            "С частотой помогают слова always, usually, sometimes, never."
        ),
        "examples": [
            "I usually wake up at seven.",
            "We work every day.",
            "She sometimes reads in the evening.",
            "They never drink coffee at night.",
        ],
        "vocabulary": [
            {"en": "wake up", "ru": "просыпаться"},
            {"en": "work", "ru": "работать"},
            {"en": "read", "ru": "читать"},
            {"en": "evening", "ru": "вечер"},
            {"en": "usually", "ru": "обычно"},
        ],
        "exercises": [
            {
                "prompt": "Переведи на английский: Я обычно просыпаюсь в семь.",
                "answers": ["i usually wake up at seven", "i usually wake up at 7"],
                "display_answer": "I usually wake up at seven.",
                "explanation": "Для регулярного действия используем Present Simple и наречие usually.",
                "skill_key": "usually",
            },
            {
                "prompt": "Заполни пропуск одним словом: We ___ every day.",
                "answers": ["work"],
                "display_answer": "work",
                "explanation": "После we используем обычную форму глагола без окончания.",
                "skill_key": "work",
            },
            {
                "prompt": "Как по-английски сказать: Она иногда читает вечером?",
                "answers": ["she sometimes reads in the evening", "she sometimes reads in evening"],
                "display_answer": "She sometimes reads in the evening.",
                "explanation": "С she глагол получает окончание -s: reads.",
                "skill_key": "read",
            },
        ],
    },
    {
        "id": 3,
        "title": "Food and ordering",
        "theory": (
            "Для заказа и разговора о еде полезны фразы I would like..., Can I have..., "
            "I like / I don't like..."
        ),
        "examples": [
            "I would like some tea.",
            "Can I have the menu, please?",
            "I like pasta.",
            "I don't like spicy food.",
        ],
        "vocabulary": [
            {"en": "tea", "ru": "чай"},
            {"en": "menu", "ru": "меню"},
            {"en": "food", "ru": "еда"},
            {"en": "spicy", "ru": "острый"},
            {"en": "would like", "ru": "хотел бы"},
        ],
        "exercises": [
            {
                "prompt": "Переведи на английский: Я хотел бы чай.",
                "answers": ["i would like some tea", "i would like tea"],
                "display_answer": "I would like some tea.",
                "explanation": "Для вежливого заказа используем I would like ...",
                "skill_key": "would like",
            },
            {
                "prompt": "Как спросить по-английски: Можно мне меню, пожалуйста?",
                "answers": ["can i have the menu, please", "can i have the menu please"],
                "display_answer": "Can I have the menu, please?",
                "explanation": "Фраза Can I have ... звучит естественно и вежливо.",
                "skill_key": "menu",
            },
            {
                "prompt": "Заполни пропуск одним словом: I don't like ___ food.",
                "answers": ["spicy"],
                "display_answer": "spicy",
                "explanation": "Spicy food означает острую еду.",
                "skill_key": "spicy",
            },
        ],
    },
    {
        "id": 4,
        "title": "Travel and city",
        "theory": (
            "Во время поездок часто нужны вопросы Where is...?, How can I get to...?, "
            "и предлоги места: near, far, next to."
        ),
        "examples": [
            "Where is the station?",
            "How can I get to the airport?",
            "The hotel is near the park.",
            "The bank is next to the cafe.",
        ],
        "vocabulary": [
            {"en": "station", "ru": "станция"},
            {"en": "airport", "ru": "аэропорт"},
            {"en": "hotel", "ru": "отель"},
            {"en": "near", "ru": "рядом"},
            {"en": "park", "ru": "парк"},
        ],
        "exercises": [
            {
                "prompt": "Как спросить по-английски: Где станция?",
                "answers": ["where is the station", "where's the station"],
                "display_answer": "Where is the station?",
                "explanation": "Для поиска места используем вопрос Where is ...?",
                "skill_key": "station",
            },
            {
                "prompt": "Переведи на английский: Как мне добраться до аэропорта?",
                "answers": ["how can i get to the airport", "how do i get to the airport"],
                "display_answer": "How can I get to the airport?",
                "explanation": "How can I get to ... подходит для вежливого вопроса о маршруте.",
                "skill_key": "airport",
            },
            {
                "prompt": "Заполни пропуск одним словом: The hotel is ___ the park.",
                "answers": ["near"],
                "display_answer": "near",
                "explanation": "Near означает рядом с чем-то.",
                "skill_key": "near",
            },
        ],
    },
    {
        "id": 5,
        "title": "Plans and free time",
        "theory": (
            "Чтобы говорить о планах, используйте going to: I am going to watch a film. "
            "Для свободного времени полезны глаголы play, watch, visit, relax."
        ),
        "examples": [
            "I am going to visit my friend.",
            "We are going to watch a film.",
            "He plays football on Sunday.",
            "She likes to relax at home.",
        ],
        "vocabulary": [
            {"en": "visit", "ru": "навещать"},
            {"en": "watch", "ru": "смотреть"},
            {"en": "film", "ru": "фильм"},
            {"en": "friend", "ru": "друг"},
            {"en": "relax", "ru": "отдыхать"},
        ],
        "exercises": [
            {
                "prompt": "Переведи на английский: Я собираюсь навестить друга.",
                "answers": ["i am going to visit my friend", "i'm going to visit my friend"],
                "display_answer": "I am going to visit my friend.",
                "explanation": "Для планов используем конструкцию be going to + глагол.",
                "skill_key": "visit",
            },
            {
                "prompt": "Заполни пропуск одним словом: We are going to ___ a film.",
                "answers": ["watch"],
                "display_answer": "watch",
                "explanation": "После going to ставится глагол в начальной форме: watch.",
                "skill_key": "watch",
            },
            {
                "prompt": "Как по-английски сказать: Она любит отдыхать дома?",
                "answers": ["she likes to relax at home", "she likes relaxing at home"],
                "display_answer": "She likes to relax at home.",
                "explanation": "После likes часто используем to + глагол для простых учебных примеров.",
                "skill_key": "relax",
            },
        ],
    },
]


def get_lesson(lesson_index: int) -> dict:
    return LESSONS[lesson_index]


def get_lesson_by_id(lesson_id: int) -> dict | None:
    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def get_all_words() -> list[dict]:
    words: list[dict] = []
    for lesson in LESSONS:
        words.extend(lesson["vocabulary"])
    return words
