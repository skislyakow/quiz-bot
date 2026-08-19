import asyncio
import os
import random

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from dotenv import load_dotenv, dotenv_values

from answer_utils import evaluate_answer
from questions import load_questions


_config = dotenv_values(".env")

redis_client = aioredis.Redis(
    host=_config.get("REDIS_HOST") or "127.0.0.1",
    port=int(_config.get("REDIS_PORT") or "6379"),
    password=_config.get("REDIS_PASSWORD") or None,
)

QUESTIONS = load_questions()

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


async def send_new_question(message: Message, state: FSMContext) -> None:
    question = random.choice(list(QUESTIONS))
    await state.update_data(question=question)
    await state.set_state(GameState.answering)
    await message.answer(question)


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.set_state(GameState.waiting_for_question)
    await message.answer("Здравствуйте", reply_markup=menu)


@router.message(F.text == "Новый вопрос")
async def handle_new_question_request(message: Message, state: FSMContext):
    await send_new_question(message, state)


@router.message(F.text == "Сдаться")
async def handle_surrender(message: Message, state: FSMContext):
    data = await state.get_data()
    question = data.get("question")
    if question is None:
        await message.answer("Активного вопроса нет - нажми 'Новый вопрос'")
        return
    correct_answer = QUESTIONS.get(question)
    await message.answer(f"Правильный ответ: {correct_answer}")
    await send_new_question(message, state)


@router.message(F.text == "Мой счёт")
async def handle_score(message: Message):
    await message.answer("Ваш счёт: 0")


@router.message(GameState.answering)
async def handle_solution_attempt(message: Message, state: FSMContext):
    if not message.text:
        return
    data = await state.get_data()
    question = data.get("question")
    correct_answer = QUESTIONS.get(question) if question is not None else None
    if correct_answer is None:
        await message.answer("Не знаю такого вопроса. Нажми 'Новый вопрос'")
        await state.set_state(GameState.waiting_for_question)
        return
    is_correct, text = evaluate_answer(message.text, correct_answer)
    await message.answer(text)
    if is_correct:
        await state.set_state(GameState.waiting_for_question)


@router.message(GameState.waiting_for_question)
async def handle_waiting(message: Message):
    await message.answer("Активного вопроса нет. Нажми 'Новый вопрос'")


async def main():
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env")

    bot = Bot(token=token)
    dp = Dispatcher(storage=RedisStorage(redis_client))
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
