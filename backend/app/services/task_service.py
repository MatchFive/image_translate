"""
任务处理服务

核心业务逻辑：协调 Excel 解析、ComfyUI 调用、OCR 验证、图片处理。
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session
from app.models.models import Task, TaskItem, TaskStatus, ItemStatus
from app.redis import get_redis, task_channel_key
from app.services.excel_service import ExcelProcessor
from app.services.comfyui_service import ComfyUIClient
from app.services.ocr_service import verify_text
from app.services.image_service import process_image

logger = logging.getLogger(__name__)
settings = get_settings()


async def publish_progress(task_id: str, message: dict):
    """
    通过 Redis PubSub 发布任务进度。

    WebSocket handler 会订阅这些消息并推送到前端。
    """
    redis = await get_redis()
    import json
    await redis.publish(
        task_channel_key(task_id),
        json.dumps(message, ensure_ascii=False),
    )


async def process_task(task_id: str, image_col: int = 1, text_col: int = 2):
    """
    异步任务处理主流程。

    完整管线：
    1. 从数据库读取任务信息
    2. 解析 Excel，提取图片和文本
    3. 逐条调用 ComfyUI 重绘
    4. OCR 验证，不通过则重试
    5. 图片后处理（透明背景、缩放）
    6. 结果写回 Excel
    7. 更新任务状态
    """
    logger.info(f"开始处理任务: {task_id}")

    async with async_session() as session:
        # ---- 读取任务 ----
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return

        try:
            # 更新任务状态为处理中
            task.status = TaskStatus.PROCESSING
            await session.commit()

            await publish_progress(task_id, {
                "type": "status",
                "task_id": task_id,
                "status": "processing",
                "message": "开始处理...",
            })

            # ---- 解析 Excel ----
            excel_processor = ExcelProcessor(task_id)
            items = excel_processor.read_excel(task.filepath, image_col=image_col, text_col=text_col)
            task.total_items = len(items)
            await session.commit()

            if not items:
                task.status = TaskStatus.FAILED
                task.error_message = "Excel 中未找到有效的图片和文本对"
                await session.commit()
                await publish_progress(task_id, {
                    "type": "status",
                    "task_id": task_id,
                    "status": "failed",
                    "message": "Excel 中未找到有效的图片和文本对",
                })
                return

            # ---- 创建 TaskItem 记录 ----
            for item in items:
                task_item = TaskItem(
                    task_id=task_id,
                    row_index=item.row_index,
                    original_image_path=item.image_path,
                    target_text=item.target_text,
                )
                session.add(task_item)
            await session.commit()

            # ---- 逐条处理 ----
            comfyui = ComfyUIClient()
            results = {}

            # 重新加载所有 items
            result = await session.execute(
                select(TaskItem).where(TaskItem.task_id == task_id)
                    .order_by(TaskItem.row_index)
            )
            task_items = result.scalars().all()

            for idx, task_item in enumerate(task_items):
                try:
                    result_path = await _process_single_item(
                        session, task, task_item, comfyui, excel_processor
                    )
                    if result_path:
                        results[task_item.row_index] = result_path

                except Exception as e:
                    logger.error(
                        f"Task {task_id}, Item {task_item.row_index}: 处理失败 - {e}"
                    )
                    task_item.status = ItemStatus.FAILED
                    task_item.error_message = str(e)
                    task.failed_items += 1
                    await session.commit()

                # 更新进度
                progress = (idx + 1) / len(task_items) * 100
                task.completed_items = sum(
                    1 for i in task_items[:idx + 1] if i.status == ItemStatus.COMPLETED
                )
                task.failed_items = sum(
                    1 for i in task_items[:idx + 1] if i.status == ItemStatus.FAILED
                )
                await session.commit()

                await publish_progress(task_id, {
                    "type": "progress",
                    "task_id": task_id,
                    "current": idx + 1,
                    "total": len(task_items),
                    "progress": round(progress, 1),
                    "item_id": task_item.id,
                    "item_status": task_item.status,
                })

            # ---- 结果写回 Excel ----
            if results:
                result_filename = f"result_{task_id}.xlsx"
                result_path = str(
                    settings.UPLOAD_DIR / task_id / result_filename
                )
                excel_processor.write_results(
                    task.filepath, results, result_path,
                    image_col=image_col,
                )
                task.result_filepath = result_path

            # ---- 更新任务最终状态 ----
            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.utcnow()
            await session.commit()

            await publish_progress(task_id, {
                "type": "status",
                "task_id": task_id,
                "status": "completed",
                "message": f"处理完成: {task.completed_items}/{task.total_items}",
            })

            logger.info(
                f"任务 {task_id} 处理完成: "
                f"{task.completed_items} 成功, {task.failed_items} 失败"
            )

        except Exception as e:
            logger.error(f"任务 {task_id} 处理异常: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.updated_at = datetime.utcnow()
            await session.commit()

            await publish_progress(task_id, {
                "type": "status",
                "task_id": task_id,
                "status": "failed",
                "message": str(e),
            })


async def _process_single_item(
    session: AsyncSession,
    task: Task,
    task_item: TaskItem,
    comfyui: ComfyUIClient,
    excel_processor: ExcelProcessor,
) -> str | None:
    """
    处理单个任务项。

    流程：
    1. 提交 ComfyUI 重绘
    2. 轮询获取结果
    3. OCR 验证，不通过则重试
    4. 图片后处理
    5. 保存结果

    Returns:
        处理后的图片路径（失败返回 None）
    """
    max_retries = settings.OCR_MAX_RETRIES
    original_image = Image.open(task_item.original_image_path)

    for attempt in range(max_retries + 1):
        # 更新状态
        if attempt > 0:
            task_item.status = ItemStatus.RETRYING
            task_item.retry_count = attempt
            await session.commit()
            logger.info(
                f"TaskItem {task_item.id}: 第 {attempt + 1} 次尝试"
            )
        else:
            task_item.status = ItemStatus.PROCESSING
            await session.commit()

        try:
            # Step 1: 提交 ComfyUI
            prompt_id = await comfyui.submit_prompt(
                image_path=task_item.original_image_path,
                target_text=task_item.target_text,
            )

            # Step 2: 轮询结果
            result_data = await comfyui.poll_result(prompt_id)

            # Step 3: 获取结果图片
            # 从 ComfyUI 输出中提取图片文件名
            outputs = result_data.get("outputs", {})
            output_images = []
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        output_images.append(img_info)

            if not output_images:
                raise ValueError("ComfyUI 未返回任何结果图片")

            # 获取第一张结果图片
            first_img = output_images[0]
            result_image = await comfyui.get_result_image(
                prompt_id, first_img["filename"]
            )

            # Step 4: OCR 验证
            task_item.status = ItemStatus.OCR_CHECKING
            await session.commit()

            is_match, ocr_text, score = verify_text(
                result_image, task_item.target_text
            )
            task_item.ocr_result = ocr_text
            task_item.ocr_match_score = score

            if not is_match and attempt < max_retries:
                logger.info(
                    f"TaskItem {task_item.id}: OCR 不匹配 "
                    f"(score={score:.2f})，将重试"
                )
                continue

            # Step 5: 图片后处理
            result_filename = f"result_{task_item.row_index}.png"
            result_path = str(
                settings.UPLOAD_DIR / task.id / result_filename
            )
            process_image(result_image, original_image, result_path)

            # Step 6: 更新结果
            task_item.result_image_path = result_path
            task_item.status = ItemStatus.COMPLETED
            await session.commit()

            return result_path

        except Exception as e:
            logger.warning(
                f"TaskItem {task_item.id}: 第 {attempt + 1} 次尝试失败 - {e}"
            )
            if attempt >= max_retries:
                task_item.status = ItemStatus.FAILED
                task_item.error_message = str(e)
                await session.commit()
                return None

    return None
