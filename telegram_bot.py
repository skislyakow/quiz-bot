import asyncio
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv


router = Router()


@router.message(CommandStart())
async def handle_start(message: Message):
    await message.answer("Здравствуйте")


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
