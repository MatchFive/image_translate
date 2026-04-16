"""
WebSocket 路由

通过 Redis PubSub 订阅任务进度，实时推送到前端。
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.redis import get_redis, task_channel_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    """
    任务进度 WebSocket 端点。

    前端连接后，通过 Redis PubSub 实时接收任务处理进度。
    """
    await websocket.accept()
    logger.info(f"WebSocket 已连接: task={task_id}")

    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = task_channel_key(task_id)

    try:
        await pubsub.subscribe(channel)

        # 持续监听 Redis 消息
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                await websocket.send_text(data)

                # 检查是否是最终状态
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "status" and parsed.get("status") in (
                        "completed", "failed"
                    ):
                        logger.info(f"WebSocket: 任务 {task_id} 已结束，关闭连接")
                        break
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: task={task_id}")
    except Exception as e:
        logger.error(f"WebSocket 异常: task={task_id}, error={e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info(f"WebSocket 清理完成: task={task_id}")
