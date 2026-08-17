import re

import pymorphy3


morph = pymorphy3.MorphAnalyzer()


def normalize_answer(text: str) -> str:
    text = text.lstrip(".,;:!?«»() \t")
    cut = len(text)
    for sep in (".", "("):
        idx = text.find(sep)
        if idx != -1:
            cut = min(cut, idx)
    result = text[:cut]
    result = re.sub(r"^[^\wа-яё]+", "", result, flags=re.I)
    result = result.strip().lower()

    tokens = re.findall(r"[a-zа-яё0-9]+", result, flags=re.I)
    lemmatized = []
    for token in tokens:
        if re.search(r"[a-zа-яё]", token, flags=re.I):
            lemmatized.append(morph.parse(token)[0].normal_form)
        else:
            lemmatized.append(token)
    return " ".join(lemmatized)
