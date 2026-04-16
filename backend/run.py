"""
FastAPI 服务启动入口

使用 uvicorn 运行，支持开发模式自动重载。
"""

import uvicorn
from app.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_DEBUG,
        log_level="info",
    )
