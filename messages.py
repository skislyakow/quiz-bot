NO_ACTIVE_QUESTION = "Активного вопроса нет. Нажмите 'Новый вопрос'"
UNKNOWN_QUESTION = "Не знаю такого вопроса. Нажмите 'Новый вопрос'"
GREETING_NO_QUESTION = f"Здравствуйте! {NO_ACTIVE_QUESTION}"
SCORE_ZERO = "Ваш счёт: 0"


def correct_answer_message(answer: str) -> str:
    return f"Правильный ответ: {answer}"
