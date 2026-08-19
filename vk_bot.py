import asyncio
import os
import random

import redis.asyncio as aioredis
from vkbottle.bot import Bot
from vkbottle.tools import Keyboard, Text
from dotenv import load_dotenv, dotenv_values

from answer_utils import evaluate_answer
from questions import load_questions


_config = dotenv_values(".env")

redis_client = aioredis.Redis(
    host=_config.get("REDIS_HOST") or "127.0.0.1",
    port=int(_config.get("REDIS_PORT") or "6379"),
    password=_config.get("REDIS_PASSWORD") or None,
    decode_responses=True,
)

QUESTIONS = load_questions()


def vk_key(uid: int) -> str:
    return f"vk_quiz:{uid}"


async def main():
    load_dotenv()
    token = os.getenv("VK_GROUP_TOKEN")

    if not token:
        raise ValueError("VK_GROUP_TOKEN не задан в .env")

    bot = Bot(token=token)
    kb = (
        Keyboard(inline=False)
        .add(Text("Новый вопрос"))
        .add(Text("Сдаться"))
        .add(Text("Мой счёт"))
    )

    @bot.on.message(text="Новый вопрос")
    async def new_question(message):
        question = random.choice(list(QUESTIONS))
        await redis_client.set(vk_key(message.peer_id), question)
        await message.answer(question, keyboard=kb)

    @bot.on.message(text="Сдаться")
    async def surrender(message):
        raw_question = await redis_client.get(vk_key(message.peer_id))
        question = (
            raw_question.decode()
            if isinstance(raw_question, bytes)
            else raw_question
        )
        if question is None:
            return await message.answer(
                "Активного вопроса нет - нажми 'Новый вопрос'"
            )
        await message.answer(f"Правильный ответ: {QUESTIONS[question]}")
        await redis_client.delete(vk_key(message.peer_id))
        new_question = random.choice(list(QUESTIONS))
        await redis_client.set(vk_key(message.peer_id), new_question)
        await message.answer(new_question, keyboard=kb)

    @bot.on.message(text="Мой счёт")
    async def score(message):
        await message.answer("Ваш счёт: 0", keyboard=kb)

    @bot.on.message()
    async def attempt(message):
        raw_question = await redis_client.get(vk_key(message.peer_id))
        question = (
            raw_question.decode()
            if isinstance(raw_question, bytes)
            else raw_question
        )
        if question is None:
            return await message.answer(
                "Активного вопроса нет. Нажми 'Новый вопрос'"
            )
        is_correct, text = evaluate_answer(message.text, QUESTIONS[question])
        await message.answer(text, keyboard=kb)
        if is_correct:
            await redis_client.delete(vk_key(message.peer_id))

    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
