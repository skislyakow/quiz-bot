import asyncio
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from dotenv import load_dotenv


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
    await message.answer("Пока здесь будет вопрос")


@router.message(F.text == "Сдаться")
async def handle_surrender(message: Message):
    await message.answer("Вы сдались")


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
