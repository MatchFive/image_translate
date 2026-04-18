"""
应用配置模块

从环境变量加载所有配置项，提供类型安全的配置访问。
"""

import os
from pathlib import Path
from functools import lru_cache

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent


@lru_cache()
def get_settings():
    """获取全局配置单例"""
    return Settings()


class Settings:
    """应用配置类，所有配置项均从环境变量读取"""

    def __init__(self):
        # ---- 应用 ----
        self.APP_NAME: str = os.getenv("APP_NAME", "ImageTranslate")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() == "true"

        # ---- PostgreSQL ----
        self.POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_USER: str = os.getenv("POSTGRES_USER", "imagetranslate")
        self.POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "imagetranslate_dev_2024")
        self.POSTGRES_DB: str = os.getenv("POSTGRES_DB", "image_translate")

        # ---- Redis ----
        self.REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
        self.REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

        # ---- ComfyUI ----
        self.COMFYUI_API_URL: str = os.getenv("COMFYUI_API_URL", "http://localhost:8001")
        self.COMFYUI_POLL_INTERVAL: int = int(os.getenv("COMFYUI_POLL_INTERVAL", "2"))
        self.COMFYUI_TIMEOUT: int = int(os.getenv("COMFYUI_TIMEOUT", "300"))

        # ---- 阿里百练 ----
        self.IMAGE_BACKEND: str = os.getenv("IMAGE_BACKEND", "bailian")  # "bailian" or "comfyui"
        self.BAILIAN_API_KEY: str = os.getenv("BAILIAN_API_KEY", "")
        self.BAILIAN_IMAGE_MODEL: str = os.getenv("BAILIAN_IMAGE_MODEL", "qwen-image-edit-plus")

        # ---- OCR 后端 ----
        self.OCR_BACKEND: str = os.getenv("OCR_BACKEND", "rapidocr")  # "rapidocr" or "bailian"

        # ---- 图片处理 ----
        self.OCR_MAX_RETRIES: int = int(os.getenv("OCR_MAX_RETRIES", "3"))
        self.OCR_MATCH_THRESHOLD: float = float(os.getenv("OCR_MATCH_THRESHOLD", "0.8"))

        # ---- 文件存储 ----
        self.UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
        self.MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(100 * 1024 * 1024)))

        # 确保上传目录存在
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def DATABASE_URL(self) -> str:
        """异步数据库连接 URL（asyncpg 驱动）"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步数据库连接 URL（用于 Alembic 迁移）"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}"
                f":{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
