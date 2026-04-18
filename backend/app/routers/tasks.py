"""
API 路由 - 任务管理

提供任务上传、查询、下载等 REST 接口。
"""

import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import Task, TaskStatus
from app.schemas import TaskResponse, TaskUploadResponse, TaskListResponse, ExcelParseResponse
from app.config import get_settings
from app.services.excel_service import ExcelProcessor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])
settings = get_settings()


@router.get("/backends", summary="获取可用的图片编辑后端列表")
async def get_available_backends():
    """检查后台配置，返回可用的重绘后端列表.

    前端根据此接口动态展示可选后端。
    """
    backends = []

    # 百练
    if settings.BAILIAN_API_KEY:
        backends.append({
            "id": "bailian",
            "name": "阿里百练",
            "description": "百练 qwen-image-edit-plus，无需本地部署",
        })

    # Nano Banana (OpenAI 兼容)
    if settings.NANO_BANANA_BASE_URL and settings.NANO_BANANA_API_KEY:
        backends.append({
            "id": "nanobanana",
            "name": "Nano Banana",
            "description": "OpenAI 兼容 images/edits 接口",
        })

    # ComfyUI
    if settings.COMFYUI_API_URL:
        backends.append({
            "id": "comfyui",
            "name": "ComfyUI",
            "description": "本地 ComfyUI 实例",
        })

    return {
        "backends": backends,
        "default": settings.IMAGE_BACKEND,
    }


@router.post("/parse-excel", response_model=ExcelParseResponse)
async def parse_excel_columns(
    file: UploadFile = File(..., description="Excel 文件（.xlsx）"),
):
    """
    上传 Excel 并解析列头信息，返回列名列表供用户选择图片列和文字列。
    文件会被临时保存，返回 temp_id 用于后续提交。
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式的 Excel 文件")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)")

    # 临时保存
    import tempfile, os
    temp_dir = tempfile.mkdtemp(prefix="excel_parse_")
    temp_path = os.path.join(temp_dir, file.filename)
    with open(temp_path, "wb") as f:
        f.write(content)

    # 解析列头
    try:
        processor = ExcelProcessor("_parse")
        columns = processor.parse_columns(temp_path)
    except Exception as e:
        logger.error(f"Excel 解析失败: {e}")
        raise HTTPException(status_code=400, detail=f"Excel 解析失败: {e}")

    # 用临时文件路径的 hash 作为 temp_id
    temp_id = os.path.basename(temp_dir)

    return ExcelParseResponse(
        temp_id=temp_id,
        temp_dir=temp_dir,
        filename=file.filename,
        columns=columns,
    )


@router.post("/upload", response_model=TaskUploadResponse)
async def upload_excel(
    file: UploadFile = File(..., description="Excel 文件（.xlsx）"),
    image_col: int = Form(1, description="图片列序号（1-based）"),
    text_col: int = Form(2, description="文字列序号（1-based）"),
    backend: str = Form(None, description="图片编辑后端: bailian / nanobanana / comfyui"),
    db: AsyncSession = Depends(get_db),
):
    """
    上传 Excel 文件，创建处理任务。

    支持用户指定哪一列是图片列、哪一列是文字列。
    上传后立即返回任务 ID，后台异步处理。
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式的 Excel 文件")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)")

    # 创建任务
    task = Task(
        filename=file.filename,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    await db.flush()

    # 保存上传文件
    task_dir = settings.UPLOAD_DIR / task.id
    task_dir.mkdir(parents=True, exist_ok=True)

    filepath = task_dir / file.filename
    with open(filepath, "wb") as f:
        f.write(content)
    task.filepath = str(filepath)
    await db.commit()

    logger.info(f"任务已创建: {task.id}, 文件: {file.filename}, 图片列={image_col}, 文字列={text_col}")

    # 解析 Excel
    try:
        processor = ExcelProcessor(task.id)
        items = processor.read_excel(filepath, image_col=image_col, text_col=text_col)
        task.total_items = len(items)
        await db.commit()
    except Exception as e:
        logger.warning(f"Excel 预解析失败（不影响后续处理）: {e}")

    # 启动后台任务处理（传入列参数）
    from app.services.task_service import process_task
    import asyncio
    asyncio.create_task(process_task(task.id, image_col=image_col, text_col=text_col, backend=backend))

    return TaskUploadResponse(
        task_id=task.id,
        message="任务创建成功，开始处理",
        total_items=task.total_items,
    )


@router.post("/upload-manual", response_model=TaskUploadResponse)
async def upload_manual(
    file: UploadFile = File(..., description="待处理的图片文件（PNG）"),
    target_text: str = File(..., description="目标替换文本"),
    backend: str = Form(None, description="图片编辑后端: bailian / nanobanana / comfyui"),
    db: AsyncSession = Depends(get_db),
):
    """
    手动上传单张图片 + 目标文本，创建处理任务。

    上传一张 PNG 图片和对应的目标替换文本，系统处理后返回结果图片。
    """
    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    if not file.filename.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="仅支持 PNG 格式图片")

    # 验证目标文本
    if not target_text or not target_text.strip():
        raise HTTPException(status_code=400, detail="目标替换文本不能为空")

    # 验证文件大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)",
        )

    # 创建任务（手动模式）
    from app.models.models import TaskSource

    task = Task(
        filename=file.filename,
        status=TaskStatus.PENDING,
        source=TaskSource.MANUAL,
    )
    db.add(task)
    await db.flush()

    # 保存上传文件
    task_dir = settings.UPLOAD_DIR / task.id
    task_dir.mkdir(parents=True, exist_ok=True)

    filepath = task_dir / file.filename
    with open(filepath, "wb") as f:
        f.write(content)

    # 创建任务子项
    from app.models.models import TaskItem, ItemStatus
    item = TaskItem(
        task_id=task.id,
        row_index=0,
        original_image_path=str(filepath),
        target_text=target_text.strip(),
        status=ItemStatus.PENDING,
    )
    db.add(item)

    task.total_items = 1
    await db.commit()

    logger.info(f"手动任务已创建: {task.id}, 图片: {file.filename}")

    # 启动后台任务处理
    from app.services.task_service import process_task
    import asyncio
    asyncio.create_task(process_task(task.id, backend=backend))

    return TaskUploadResponse(
        task_id=task.id,
        message="手动任务创建成功，开始处理",
        total_items=1,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """查询任务状态和进度"""
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表"""
    # 查询总数
    count_result = await db.execute(select(Task))
    total = len(count_result.scalars().all())

    # 分页查询
    result = await db.execute(
        select(Task)
        .order_by(Task.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    tasks = result.scalars().all()

    return TaskListResponse(tasks=tasks, total=total)


@router.get("/{task_id}/download")
async def download_result(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """下载处理结果（Excel 文件或结果图片）"""
    from fastapi.responses import FileResponse
    from app.models.models import TaskSource, TaskItem

    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")

    # Excel 模式：下载结果 Excel
    if task.source == TaskSource.EXCEL:
        if not task.result_filepath or not Path(task.result_filepath).exists():
            raise HTTPException(status_code=404, detail="结果文件不存在")
        return FileResponse(
            task.result_filepath,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"result_{task.filename}",
        )

    # 手动模式：下载结果图片
    item_result = await db.execute(
        select(TaskItem).where(TaskItem.task_id == task_id).limit(1)
    )
    item = item_result.scalar_one_or_none()
    if not item or not item.result_image_path or not Path(item.result_image_path).exists():
        raise HTTPException(status_code=404, detail="结果图片不存在")

    return FileResponse(
        item.result_image_path,
        media_type="image/png",
        filename=f"result_{Path(item.original_image_path).name}",
    )


@router.get("/{task_id}/images/{image_type}/{item_id}")
async def get_task_image(
    task_id: str,
    image_type: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取任务的原始/处理后图片"""
    from fastapi.responses import FileResponse
    from app.models.models import TaskItem

    if image_type not in ("original", "result"):
        raise HTTPException(status_code=400, detail="image_type 必须为 original 或 result")

    result = await db.execute(
        select(TaskItem).where(
            TaskItem.id == item_id,
            TaskItem.task_id == task_id,
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="任务项不存在")

    image_path = item.original_image_path if image_type == "original" else item.result_image_path
    if not image_path or not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(image_path, media_type="image/png")
