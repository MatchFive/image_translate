"""
Pydantic Schema 定义

用于 API 请求/响应的数据验证和序列化。
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ============================================
# Task 相关 Schema
# ============================================

class TaskItemResponse(BaseModel):
    """任务子项响应"""
    id: str
    row_index: int
    target_text: str
    status: str
    retry_count: int = 0
    ocr_result: str | None = None
    ocr_match_score: float | None = None
    error_message: str | None = None
    original_image_url: str | None = None
    result_image_url: str | None = None

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """任务详情响应"""
    id: str
    filename: str
    status: str
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    progress: float = 0.0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[TaskItemResponse] = []

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[TaskResponse]
    total: int


class TaskUploadResponse(BaseModel):
    """上传任务创建响应"""
    task_id: str
    message: str
    total_items: int


# ============================================
# WebSocket 消息 Schema
# ============================================

class WSProgressMessage(BaseModel):
    """WebSocket 进度推送消息"""
    type: str = "progress"
    task_id: str
    current: int
    total: int
    progress: float
    item_id: str | None = None
    item_status: str | None = None
    item_message: str | None = None


class WSStatusMessage(BaseModel):
    """WebSocket 状态变更消息"""
    type: str = "status"
    task_id: str
    status: str
    message: str | None = None


class WSErrorMessage(BaseModel):
    """WebSocket 错误消息"""
    type: str = "error"
    task_id: str
    message: str
