"""
FastAPI 应用入口

初始化应用、注册路由、配置中间件和生命周期事件。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.redis import get_redis, close_redis
from app.routers.tasks import router as tasks_router
from app.routers.ws import router as ws_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"🚀 {settings.APP_NAME} 启动中...")
    await init_db()
    await get_redis()
    logger.info("✅ 数据库和 Redis 连接就绪")

    yield

    # 关闭时
    await close_redis()
    logger.info("👋 应用已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="图片文字翻译替换工具",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件（开发环境允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/")
async def root():
    """根路径"""
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }
