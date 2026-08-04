"""Background jobs with arq. Run the worker: `arq app.integrations.tasks.WorkerSettings`.

Enqueue from an endpoint:
    from arq import create_pool
    from arq.connections import RedisSettings
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job("send_welcome_email", user_id, email)
"""
from arq.connections import RedisSettings

from app.core.config import settings


async def send_welcome_email(ctx, user_id: int, email: str) -> str:
    """Pretend-slow email send — offloaded so registration returns instantly."""
    # In production: call your email provider here.
    result = f"welcome email queued for {email} (user {user_id})"
    await ctx["redis"].set(f"welcome:{user_id}", result, ex=3600)
    return result


class WorkerSettings:
    functions = [send_welcome_email]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
