import pathlib
import re


def load_questions(folder="quiz-questions") -> dict[str, str]:
    bank = {}
    for path in pathlib.Path(folder).glob("*.txt"):
        with open(path, encoding="koi8-r") as f:
            text = f.read()
        current_question = None
        sections = text.split("\n\n")
        for section in sections:
            label = section.split("\n", 1)[0].rstrip(" :").strip()
            if re.match(r"^Вопрос\s*\d", label, re.I):
                current_question = section.split("\n", 1)[1].strip()
            elif label.lower() == "ответ" and current_question:
                bank[current_question] = section.split("\n", 1)[1].strip()
    return bank


print(len(load_questions()))
