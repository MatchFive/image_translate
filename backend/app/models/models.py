"""
数据模型定义

定义 Task（任务）和 TaskItem（子项）的 ORM 模型。
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, Float, Enum, DateTime, ForeignKey, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskSource(str, enum.Enum):
    """任务来源枚举"""
    EXCEL = "excel"              # Excel 批量上传
    MANUAL = "manual"            # 手动单张上传


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 处理失败


class ItemStatus(str, enum.Enum):
    """子项状态枚举"""
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 处理中
    OCR_CHECKING = "ocr_checking"  # OCR 验证中
    RETRYING = "retrying"        # 重试中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 处理失败


class Task(Base):
    """任务模型 - 对应一次 Excel 上传处理"""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[TaskSource] = mapped_column(
        Enum(TaskSource), default=TaskSource.EXCEL, comment="任务来源"
    )
    filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="原始文件名（Excel模式）"
    )
    filepath: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="服务器存储路径（Excel模式）"
    )
    result_filepath: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="结果文件路径"
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态"
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0, comment="总条目数")
    completed_items: Mapped[int] = mapped_column(Integer, default=0, comment="已完成条目数")
    failed_items: Mapped[int] = mapped_column(Integer, default=0, comment="失败条目数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 关联
    items: Mapped[list["TaskItem"]] = relationship(
        "TaskItem", back_populates="task", cascade="all, delete-orphan"
    )

    @property
    def progress(self) -> float:
        """计算处理进度百分比"""
        if self.total_items == 0:
            return 0.0
        return round((self.completed_items + self.failed_items) / self.total_items * 100, 1)


class TaskItem(Base):
    """任务子项模型 - 对应 Excel 中的每一行"""
    __tablename__ = "task_items"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id", ondelete="CASCADE"), comment="所属任务ID"
    )
    row_index: Mapped[int] = mapped_column(Integer, comment="Excel 行号（0-based）")
    original_image_path: Mapped[str] = mapped_column(String(512), comment="原始图片路径")
    target_text: Mapped[str] = mapped_column(Text, comment="目标替换文本")
    result_image_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="处理后图片路径"
    )
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus), default=ItemStatus.PENDING, comment="子项状态"
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="已重试次数")
    ocr_result: Mapped[str | None] = mapped_column(Text, nullable=True, comment="OCR 识别结果")
    ocr_match_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="OCR 匹配分数"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, comment="额外元数据"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 关联
    task: Mapped["Task"] = relationship("Task", back_populates="items")
