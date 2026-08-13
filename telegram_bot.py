import asyncio
import os
import random

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from dotenv import load_dotenv, dotenv_values

from questions import load_questions

_config = dotenv_values(".env")

redis_client = aioredis.Redis(
    host=_config.get("REDIS_HOST") or "127.0.0.1",
    port=int(_config.get("REDIS_PORT") or "6379"),
    password=_config.get("REDIS_PASSWORD") or None,
    decode_responses=True,
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


@router.message(CommandStart())
async def handle_start(message: Message):
    await message.answer("Здравствуйте", reply_markup=menu)


@router.message(F.text == "Новый вопрос")
async def handle_new_question(message: Message):
    if message.from_user is None:
        return

    question = random.choice(list(QUESTIONS))
    await redis_client.set(f"quiz:{message.from_user.id}", question)
    await message.answer(question)


@router.message(F.text == "Сдаться")
async def handle_surrender(message: Message):
    if message.from_user is None:
        return

    question = await redis_client.get(f"quiz:{message.from_user.id}")
    if question is None:
        await message.answer("Активного вопроса нет - нажми 'Новый вопрос'")
        return
    if isinstance(question, bytes):
        question = question.decode()

    answer = QUESTIONS.get(question)
    await message.answer(f"Правильный ответ: {answer}")


@router.message(F.text == "Мой счёт")
async def handle_score(message: Message):
    await message.answer("Ваш счёт: 0")


@router.message()
async def handle_echo(message: Message):
    if message.text:
        await message.answer(message.text)


async def main():
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env")

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
