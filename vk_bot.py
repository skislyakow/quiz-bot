import asyncio
import os

from vkbottle.bot import Bot
from vkbottle.tools import Keyboard, Text
from dotenv import load_dotenv

from answer_utils import evaluate_answer
from db import create_redis_client
from messages import (
    NO_ACTIVE_QUESTION,
    GREETING_NO_QUESTION,
    SCORE_ZERO,
    correct_answer_message,
)
from questions import load_questions, random_question


QUESTIONS = load_questions()
QUESTION_TTL = 3600

redis_client = create_redis_client(decode_responses=True)


def vk_key(uid: int) -> str:
    return f"vk_quiz:{uid}"


async def get_active_question(peer_id: int) -> str | None:
    raw_question = await redis_client.get(vk_key(peer_id))
    return (
        raw_question.decode()
        if isinstance(raw_question, bytes)
        else raw_question
    )


async def main():
    load_dotenv()
    token = os.getenv("VK_GROUP_TOKEN")

    if not token:
        raise ValueError("VK_GROUP_TOKEN не задан в .env")

    bot = Bot(token=token)
    kb = (
        Keyboard(inline=False)
        .add(Text("Новый вопрос"))
        .row()
        .add(Text("Сдаться"))
        .row()
        .add(Text("Мой счёт"))
    )

    @bot.on.message(text="Новый вопрос")
    async def new_question(message):
        question = random_question()
        await redis_client.set(
            vk_key(message.peer_id), question, ex=QUESTION_TTL
        )
        await message.answer(question, keyboard=kb)

    @bot.on.message(text="Сдаться")
    async def surrender(message):
        question = await get_active_question(message.peer_id)
        if question is None:
            return await message.answer(
                NO_ACTIVE_QUESTION,
                keyboard=kb,
            )
        await message.answer(correct_answer_message(QUESTIONS[question]))
        await redis_client.delete(vk_key(message.peer_id))
        next_question = random_question()
        await redis_client.set(
            vk_key(message.peer_id), next_question, ex=QUESTION_TTL
        )
        await message.answer(next_question, keyboard=kb)

    @bot.on.message(text="Мой счёт")
    async def score(message):
        await message.answer(SCORE_ZERO, keyboard=kb)

    @bot.on.message()
    async def attempt(message):
        question = await get_active_question(message.peer_id)
        if question is None:
            return await message.answer(
                GREETING_NO_QUESTION,
                keyboard=kb,
            )
        is_correct, text = evaluate_answer(message.text, QUESTIONS[question])
        await message.answer(text, keyboard=kb)
        if is_correct:
            await redis_client.delete(vk_key(message.peer_id))

    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
