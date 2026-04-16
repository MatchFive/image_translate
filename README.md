# Image Translate - 图片文字智能替换工具

基于前后端分离架构的图片文字替换工具。上传包含图片和目标文本的 Excel 表格，自动通过 ComfyUI 重绘图片中的文字。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus |
| 后端 | FastAPI + SQLAlchemy + asyncpg |
| 队列 | Redis |
| 数据库 | PostgreSQL 16 |
| 图片处理 | OpenCV + rapidocr-onnxruntime |
| AI 重绘 | ComfyUI API |

## 功能流程

1. 用户上传 Excel 文件（第一列=图片，第二列=替换文本）
2. 系统逐行处理，调用 ComfyUI API 进行文字重绘
3. 本地 OCR 识别验证生成文字是否匹配，不匹配自动重试（最多3次）
4. OpenCV 处理透明背景图片
5. 缩放结果图到原始尺寸
6. 结果写入 Excel 第三列，供用户下载

## 快速开始

### 前置条件

- Docker & Docker Compose
- Node.js >= 18
- Python >= 3.11
- ComfyUI 运行在 localhost:8001

### 1. 启动后端服务

```bash
# 配置环境变量
cp .env.example .env
# 按需编辑 .env

# 启动 PostgreSQL + Redis + Backend
docker-compose up -d
```

### 2. 启动前端开发服务

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

### 3. 本地开发模式（不用 Docker）

```bash
# 启动 PostgreSQL 和 Redis（或使用已有服务）
docker-compose up -d postgres redis

# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py

# 前端
cd frontend
npm install
npm run dev
```

## 项目结构

```
image_translate/
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── api/            # API 调用
│   │   ├── components/     # 公共组件
│   │   ├── views/          # 页面
│   │   ├── router/         # 路由
│   │   └── types/          # 类型定义
│   ├── vite.config.ts
│   └── package.json
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   ├── models/         # 数据库模型
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库连接
│   │   └── main.py         # 应用入口
│   ├── workflows/          # ComfyUI 工作流 JSON
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env
└── .gitignore
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks/upload` | 上传 Excel 创建任务 |
| GET | `/api/tasks/{task_id}` | 查询任务状态 |
| GET | `/api/tasks/{task_id}/download` | 下载结果 Excel |
| WS | `/ws/tasks/{task_id}` | 实时进度推送 |

## 配置 ComfyUI 工作流

将你的工作流 JSON 放到 `backend/workflows/workflow.json`，系统会读取并提交到 ComfyUI API。

当前为占位空文件，待后续实现具体工作流。
