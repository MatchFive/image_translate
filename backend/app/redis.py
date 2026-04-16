"""
Redis 连接管理

提供 Redis 异步客户端的单例管理。
"""

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

# 全局 Redis 连接池
_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 异步客户端"""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis():
    """关闭 Redis 连接"""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


# ---- 任务状态缓存 Key 定义 ----

def task_cache_key(task_id: str) -> str:
    """任务状态缓存 key"""
    return f"task:{task_id}:status"


def task_progress_key(task_id: str) -> str:
    """任务进度缓存 key"""
    return f"task:{task_id}:progress"


def task_channel_key(task_id: str) -> str:
    """WebSocket 广播频道 key"""
    return f"task:{task_id}:channel"
