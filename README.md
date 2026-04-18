# Image Translate - 图片文字智能替换工具

基于前后端分离架构的图片文字替换工具。上传包含图片和目标文本的 Excel 表格，自动通过 AI 重绘图片中的文字。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus |
| 后端 | FastAPI + SQLAlchemy + asyncpg |
| 队列 | Redis |
| 数据库 | PostgreSQL 16 |
| 图片处理 | OpenCV + Pillow + NumPy |
| AI 重绘 | 阿里百练 (qwen-image-edit-plus) / ComfyUI |
| OCR 验证 | RapidOCR / 百炼千帆 OCR |

## 功能流程

1. 用户上传 Excel 文件（可自定义图片列和文字列）
2. 系统逐行处理，调用 AI 进行文字重绘
3. 本地 OCR 识别验证生成文字是否匹配，不匹配自动重试（最多3次）
4. 极端宽高比图片自动补透明边，生成后裁剪回原尺寸
5. 结果缩放到原图尺寸，去黑背景变透明
6. 结果写入 Excel，供用户下载

## 图片编辑后端

支持两种后端，通过 `IMAGE_BACKEND` 环境变量切换：

### 阿里百练（默认）

使用百练多模态 API（qwen-image-edit-plus），无需部署本地模型。

```env
IMAGE_BACKEND=bailian
BAILIAN_API_KEY=your-api-key
BAILIAN_IMAGE_MODEL=qwen-image-edit-plus
```

### ComfyUI

使用本地 ComfyUI 实例，需要自行部署。

```env
IMAGE_BACKEND=comfyui
COMFYUI_API_URL=http://localhost:8001
```

## 快速开始

### 前置条件

- Docker & Docker Compose
- Node.js >= 18
- Python >= 3.11

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 BAILIAN_API_KEY 等配置
```

### 2. 启动后端服务

```bash
# 启动 PostgreSQL + Redis + Backend
docker-compose up -d
```

### 3. 启动前端开发服务

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

### 4. 本地开发模式（不用 Docker）

```bash
# 启动 PostgreSQL 和 Redis
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
│   │   │   ├── bailian_service.py    # 百练图片编辑（默认）
│   │   │   ├── comfyui_service.py    # ComfyUI 图片编辑
│   │   │   ├── task_service.py       # 任务调度
│   │   │   ├── ocr_service.py        # OCR 验证
│   │   │   ├── image_service.py      # 图片后处理
│   │   │   └── excel_service.py      # Excel 解析
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

## 配置说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `IMAGE_BACKEND` | `bailian` | 图片编辑后端：bailian / comfyui |
| `BAILIAN_API_KEY` | - | 百练 API Key |
| `BAILIAN_IMAGE_MODEL` | `qwen-image-edit-plus` | 百练图片编辑模型 |
| `OCR_BACKEND` | `rapidocr` | OCR 后端：rapidocr / bailian |
| `OCR_MAX_RETRIES` | `3` | OCR 验证最大重试次数 |
| `OCR_MATCH_THRESHOLD` | `0.8` | OCR 匹配阈值 |
| `COMFYUI_API_URL` | `http://localhost:8001` | ComfyUI 地址 |

## License

MIT
