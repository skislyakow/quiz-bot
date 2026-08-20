import pathlib
import pickle
import random
import re


_CACHE_FILE = ".questions_cache.pkl"
_question_keys: list[str] = []
_questions: dict[str, str] = {}
_comments: dict[str, str] = {}


def _strip_handout(text: str) -> str:
    text = re.sub(r"(?is)<раздатка>.*?</раздатка>", "", text)
    text = re.sub(r"(?is)\[раздатка\].*?\[/раздатка\]", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _sources_fingerprint(folder: str) -> str | None:
    paths = sorted(pathlib.Path(folder).glob("*.txt"))
    if not paths:
        return None
    parts = []
    for path in paths:
        stat = path.stat()
        parts.append(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
    return "|".join(parts)


def _parse_questions(folder: str) -> tuple[dict[str, str], dict[str, str]]:
    questions: dict[str, str] = {}
    comments: dict[str, str] = {}
    for path in pathlib.Path(folder).glob("*.txt"):
        with open(path, encoding="koi8-r") as f:
            text = f.read()
        current_question = None
        sections = text.split("\n\n")
        for section in sections:
            label = section.split("\n", 1)[0].rstrip(" :").strip()
            if re.match(r"^Вопрос\s*\d", label, re.I):
                current_question = _strip_handout(section.split("\n", 1)[1])
            elif label.lower() == "ответ" and current_question:
                questions[current_question] = section.split("\n", 1)[1].strip()
            elif label.lower().startswith("комментарий") and current_question:
                comments[current_question] = section.split("\n", 1)[1].strip()
    return questions, comments


def _load_from_cache(
    folder: str,
) -> tuple[dict[str, str], dict[str, str]] | None:
    cache_path = pathlib.Path(_CACHE_FILE)
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "rb") as f:
            fingerprint, questions, comments = pickle.load(f)
    except (
        OSError,
        pickle.UnpicklingError,
        EOFError,
        AttributeError,
        ImportError,
        IndexError,
        ValueError,
        TypeError,
    ):
        return None
    if fingerprint != _sources_fingerprint(folder):
        return None
    return questions, comments


def _save_to_cache(
    folder: str, questions: dict[str, str], comments: dict[str, str]
) -> None:
    fingerprint = _sources_fingerprint(folder)
    if fingerprint is None:
        return
    tmp_path = pathlib.Path(f"{_CACHE_FILE}.tmp")
    try:
        with open(tmp_path, "wb") as f:
            pickle.dump(
                (fingerprint, questions, comments),
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        tmp_path.replace(pathlib.Path(_CACHE_FILE))
    except OSError:
        tmp_path.unlink(missing_ok=True)


def _ensure_loaded(folder: str = "quiz-questions") -> None:
    cached_data = _load_from_cache(folder)
    if cached_data is None:
        questions, comments = _parse_questions(folder)
        _save_to_cache(folder, questions, comments)
    else:
        questions, comments = cached_data
        _questions.clear()
        _questions.update(questions)
        _comments.clear()
        _comments.update(comments)
        _question_keys[:] = list(_questions)


def load_questions(folder="quiz-questions") -> dict[str, str]:
    _ensure_loaded(folder)
    return _questions


def load_comments(folder="quiz-questions") -> dict[str, str]:
    _ensure_loaded(folder)
    return _comments


def random_question() -> str:
    return random.choice(_question_keys)
