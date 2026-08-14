def normalize_answer(text: str) -> str:
    cut = len(text)
    for sep in (".", "("):
        idx = text.find(sep)
        if idx != -1:
            cut = min(cut, idx)
    return text[:cut].strip().lower()
