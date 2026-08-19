import pathlib
import pickle
import random
import re


_CACHE_FILE = ".questions_cache.pkl"
_question_keys: list[str] = []


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


def _parse_questions(folder: str) -> dict[str, str]:
    questions = {}
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
    return questions


def _load_from_cache(folder: str) -> dict[str, str] | None:
    cache_path = pathlib.Path(_CACHE_FILE)
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "rb") as f:
            fingerprint, questions = pickle.load(f)
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
    return questions


def _save_to_cache(folder: str, questions: dict[str, str]) -> None:
    fingerprint = _sources_fingerprint(folder)
    if fingerprint is None:
        return
    tmp_path = pathlib.Path(f"{_CACHE_FILE}.tmp")
    try:
        with open(tmp_path, "wb") as f:
            pickle.dump(
                (fingerprint, questions), f, protocol=pickle.HIGHEST_PROTOCOL
            )
        tmp_path.replace(pathlib.Path(_CACHE_FILE))
    except OSError:
        tmp_path.unlink(missing_ok=True)


def load_questions(folder="quiz-questions") -> dict[str, str]:
    questions = _load_from_cache(folder)
    if questions is None:
        questions = _parse_questions(folder)
        _save_to_cache(folder, questions)
    _question_keys[:] = list(questions)
    return questions


def random_question() -> str:
    return random.choice(_question_keys)
