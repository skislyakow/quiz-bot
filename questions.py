import pathlib
import re


def _strip_handout(text: str) -> str:
    text = re.sub(r"(?is)<раздатка>.*?</раздатка>", "", text)
    text = re.sub(r"(?is)\[раздатка\].*?\[/раздатка\]", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def load_questions(folder="quiz-questions") -> dict[str, str]:
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
