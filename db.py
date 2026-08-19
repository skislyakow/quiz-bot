import redis.asyncio as aioredis
from dotenv import dotenv_values


_config = dotenv_values(".env")


def create_redis_client(decode_responses: bool = False) -> aioredis.Redis:
    return aioredis.Redis(
        host=_config.get("REDIS_HOST") or "127.0.0.1",
        port=int(_config.get("REDIS_PORT") or "6379"),
        password=_config.get("REDIS_PASSWORD") or None,
        decode_responses=decode_responses,
    )
