import asyncio
import os
import argparse

from vkbottle.bot import Bot
from vkbottle.tools import Keyboard, Text
from dotenv import load_dotenv

from answer_utils import evaluate_answer, mask_answer_in_explanation
from db import create_redis_client
from messages import (
    NO_ACTIVE_QUESTION,
    GREETING_NO_QUESTION,
    SCORE_ZERO,
    correct_answer_message,
    explanation_message,
)
from questions import load_questions, random_question, load_comments


QUESTION_TTL = 3600

redis_client = create_redis_client(decode_responses=True)


def vk_key(uid: int) -> str:
    return f"vk_quiz:{uid}"


def vk_hint_key(uid: int) -> str:
    return f"vk_hint:{uid}"


async def get_active_question(peer_id: int) -> str | None:
    raw_question = await redis_client.get(vk_key(peer_id))
    return (
        raw_question.decode()
        if isinstance(raw_question, bytes)
        else raw_question
    )


async def main():
    parser = argparse.ArgumentParser(description="VK quiz bot")
    parser.add_argument(
        "--questions-dir",
        default="quiz-questions",
        help="Папка с файлами вопросов (*.txt, KOI8-R)",
    )
    args = parser.parse_args()

    questions = load_questions(args.questions_dir)
    comments = load_comments(args.questions_dir)

    load_dotenv()
    token = os.getenv("VK_GROUP_TOKEN")

    if not token:
        raise ValueError("VK_GROUP_TOKEN не задан в .env")

    bot = Bot(token=token)
    keyboard = (
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
        await redis_client.delete(vk_hint_key(message.peer_id))
        await message.answer(question, keyboard=keyboard)

    @bot.on.message(text="Сдаться")
    async def surrender(message):
        question = await get_active_question(message.peer_id)
        if question is None:
            return await message.answer(
                NO_ACTIVE_QUESTION,
                keyboard=keyboard,
            )
        answer_text = correct_answer_message(questions[question])
        comment = comments.get(question)
        if comment:
            answer_text = f"{answer_text}\n\n{explanation_message(comment)}"
        await message.answer(answer_text, keyboard=keyboard)
        await redis_client.delete(vk_key(message.peer_id))
        await redis_client.delete(vk_hint_key(message.peer_id))
        next_question = random_question()
        await redis_client.set(
            vk_key(message.peer_id), next_question, ex=QUESTION_TTL
        )
        await message.answer(next_question, keyboard=keyboard)

    @bot.on.message(text="Мой счёт")
    async def score(message):
        await message.answer(SCORE_ZERO, keyboard=keyboard)

    @bot.on.message()
    async def attempt(message):
        question = await get_active_question(message.peer_id)
        if not message.text:
            return
        if question is None:
            return await message.answer(
                GREETING_NO_QUESTION,
                keyboard=keyboard,
            )
        is_correct, feedback = evaluate_answer(
            message.text, questions[question]
        )
        if is_correct:
            await redis_client.delete(vk_key(message.peer_id))
            await redis_client.delete(vk_hint_key(message.peer_id))
            await message.answer(feedback, keyboard=keyboard)
        else:
            if await redis_client.get(vk_hint_key(message.peer_id)) is None:
                comment = comments.get(question)
                if comment:
                    masked = mask_answer_in_explanation(
                        comment, questions[question]
                    )
                    feedback = f"{feedback}\n\n{explanation_message(masked)}"
                await redis_client.set(
                    vk_hint_key(message.peer_id), "1", ex=QUESTION_TTL
                )
            await message.answer(feedback, keyboard=keyboard)

    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
