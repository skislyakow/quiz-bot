import re

import pymorphy3  # type: ignore[import-untyped]


morph_analyzer = pymorphy3.MorphAnalyzer()


def normalize_answer(text: str) -> str:
    text = text.lstrip(".,;:!?«»() \t")
    truncated_index = len(text)
    for separator in (".", "("):
        idx = text.find(separator)
        if idx != -1:
            truncated_index = min(truncated_index, idx)
    stripped_text = text[:truncated_index]
    stripped_text = re.sub(r"^[^\wа-яё]+", "", stripped_text, flags=re.I)
    stripped_text = stripped_text.strip().lower()

    tokens = re.findall(r"[a-zа-яё0-9]+", stripped_text, flags=re.I)
    lemmatized_tokens = []
    for token in tokens:
        if re.search(r"[a-zа-яё]", token, flags=re.I):
            lemmatized_tokens.append(
                morph_analyzer.parse(token)[0].normal_form
            )
        else:
            lemmatized_tokens.append(token)
    return " ".join(lemmatized_tokens)


def evaluate_answer(user_text: str, correct_text: str) -> tuple[bool, str]:
    normalized_user_answer = normalize_answer(user_text)
    normalized_correct_answer = normalize_answer(correct_text)
    if normalized_user_answer == normalized_correct_answer or (
        len(normalized_user_answer) >= 3
        and normalized_user_answer in normalized_correct_answer  # noqa: W503
    ):
        return (
            True,
            "Правильно! Поздравляю! Для следующего вопроса нажми "
            "'Новый вопрос'",
        )
    return False, "Неправильно... Попробуешь еще раз?"


def mask_answer_in_explanation(explanation: str, correct_text: str) -> str:
    phrase = correct_text.strip()
    for separator in (".", "(", "\n"):
        idx = phrase.find(separator)
        if idx != -1:
            phrase = phrase[:idx]
    phrase = phrase.strip()
    if not phrase:
        return explanation
    pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
    return pattern.sub("…", explanation)
