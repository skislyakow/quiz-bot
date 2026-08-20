import argparse
import asyncio
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from dotenv import load_dotenv

from answer_utils import evaluate_answer
from db import create_redis_client
from messages import (
    NO_ACTIVE_QUESTION,
    UNKNOWN_QUESTION,
    GREETING_NO_QUESTION,
    SCORE_ZERO,
    correct_answer_message,
    explanation_message,
)
from questions import load_questions, random_question, load_comments


redis_client = create_redis_client()
router = Router()

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Новый вопрос")],
        [KeyboardButton(text="Сдаться")],
        [KeyboardButton(text="Мой счёт")],
    ],
    is_persistent=True,
    resize_keyboard=True,
)


class GameState(StatesGroup):
    waiting_for_question = State()
    answering = State()


async def main():
    parser = argparse.ArgumentParser(description="Telegram quiz bot")
    parser.add_argument(
        "--questions-dir",
        default="quiz-questions",
        help="Папка с файлами вопросов (*.txt, KOI8-R)",
    )
    args = parser.parse_args()
    questions = load_questions(args.questions_dir)
    comments = load_comments(args.questions_dir)

    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env")

    bot = Bot(token=token)
    dp = Dispatcher(storage=RedisStorage(redis_client))
    dp.include_router(router)

    async def send_new_question(message: Message, state: FSMContext) -> None:
        question = random_question()
        await state.update_data(question=question, hinted=False)
        await state.set_state(GameState.answering)
        await message.answer(question)

    @router.message(CommandStart())
    async def handle_start(message: Message, state: FSMContext):
        await state.set_state(GameState.waiting_for_question)
        await message.answer(GREETING_NO_QUESTION, reply_markup=menu)

    @router.message(F.text == "Новый вопрос")
    async def handle_new_question_request(message: Message, state: FSMContext):
        await send_new_question(message, state)

    @router.message(F.text == "Сдаться")
    async def handle_surrender(message: Message, state: FSMContext):
        state_data = await state.get_data()
        question = state_data.get("question")
        if question is None:
            await message.answer(NO_ACTIVE_QUESTION)
            return
        correct_answer = questions[question]
        reply_text = correct_answer_message(correct_answer)
        comment = comments.get(question)
        if comment:
            reply_text = f"{reply_text}\n\n{explanation_message(comment)}"
        await message.answer(reply_text)
        await send_new_question(message, state)

    @router.message(F.text == "Мой счёт")
    async def handle_score(message: Message):
        await message.answer(SCORE_ZERO)

    @router.message(GameState.answering)
    async def handle_solution_attempt(message: Message, state: FSMContext):
        if not message.text:
            return
        state_data = await state.get_data()
        raw_question = state_data.get("question")
        if raw_question is None:
            await message.answer(UNKNOWN_QUESTION)
            await state.set_state(GameState.waiting_for_question)
            return
        question: str = raw_question
        correct_answer = (
            questions.get(question) if question is not None else None
        )
        if correct_answer is None:
            await message.answer(UNKNOWN_QUESTION)
            await state.set_state(GameState.waiting_for_question)
            return
        is_correct, feedback = evaluate_answer(message.text, correct_answer)
        if is_correct:
            await message.answer(feedback)
            await state.set_state(GameState.waiting_for_question)
        else:
            if not state_data.get("hinted"):
                comment = comments.get(question)
                if comment:
                    feedback = f"{feedback}\n\n{explanation_message(comment)}"
                await state.update_data(hinted=True)
            await message.answer(feedback)

    @router.message(GameState.waiting_for_question)
    async def handle_waiting(message: Message):
        await message.answer(NO_ACTIVE_QUESTION)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
