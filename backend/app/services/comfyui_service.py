"""
ComfyUI API 客户端

负责与 ComfyUI 后端交互，提交工作流、轮询结果。
"""

import json
import asyncio
import logging
import io
import urllib.parse
from pathlib import Path

import httpx
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 工作流目录
WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"


class ComfyUIClient:
    """ComfyUI API 客户端"""

    def __init__(self):
        self.base_url = settings.COMFYUI_API_URL
        self.poll_interval = settings.COMFYUI_POLL_INTERVAL
        self.timeout = settings.COMFYUI_TIMEOUT

    def load_workflow(self, workflow_name: str = "workflow.json") -> dict:
        """
        加载工作流 JSON 配置。

        Args:
            workflow_name: 工作流文件名

        Returns:
            工作流配置字典
        """
        workflow_path = WORKFLOWS_DIR / workflow_name
        if not workflow_path.exists():
            logger.warning(f"工作流文件不存在: {workflow_path}，使用空配置")
            return {}

        with open(workflow_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def submit_prompt(
        self,
        image_path: str,
        target_text: str,
        workflow_name: str = "workflow.json",
    ) -> str:
        """
        向 ComfyUI 提交重绘任务。

        Args:
            image_path: 原始图片路径
            target_text: 目标替换文本
            workflow_name: 工作流文件名

        Returns:
            prompt_id（ComfyUI 任务 ID）

        处理逻辑：
        1. 加载工作流 JSON
        2. 注入图片路径和目标文本参数
        3. POST 提交到 /prompt 接口
        """
        workflow = self.load_workflow(workflow_name)

        # TODO: 根据实际工作流结构注入参数
        # 以下为示例结构，需根据 ComfyUI 工作流实际节点 ID 和参数调整
        # workflow["nodes"][0]["inputs"]["image"] = image_path
        # workflow["nodes"][1]["inputs"]["text"] = target_text

        payload = {
            "prompt": workflow,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/prompt",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            prompt_id = data.get("prompt_id")
            logger.info(f"ComfyUI prompt submitted: {prompt_id}")
            return prompt_id

    async def poll_result(self, prompt_id: str) -> dict:
        """
        轮询 ComfyUI 获取任务执行状态和结果。

        Args:
            prompt_id: ComfyUI 任务 ID

        Returns:
            结果字典，包含 status 和 outputs

        轮询策略：
        - 每隔 poll_interval 秒查询一次 /history/{prompt_id}
        - 超时 timeout 秒后抛出异常
        """
        elapsed = 0
        async with httpx.AsyncClient(timeout=30) as client:
            while elapsed < self.timeout:
                try:
                    resp = await client.get(
                        f"{self.base_url}/history/{prompt_id}",
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        # 检查是否已完成
                        if prompt_id in data:
                            status = data[prompt_id].get("status", {})
                            if status.get("completed", False) or status.get("status_str") == "success":
                                logger.info(f"ComfyUI prompt {prompt_id} completed")
                                return data[prompt_id]
                except httpx.HTTPError as e:
                    logger.warning(f"ComfyUI poll error: {e}")

                await asyncio.sleep(self.poll_interval)
                elapsed += self.poll_interval

        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out after {self.timeout}s")

    async def get_result_image(self, prompt_id: str, filename: str) -> Image.Image:
        """
        从 ComfyUI 获取结果图片。

        Args:
            prompt_id: ComfyUI 任务 ID
            filename: 输出文件名（从 history 结果中获取）

        Returns:
            PIL Image 对象
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{self.base_url}/view",
                params={"filename": filename, "type": "output"},
            )
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content))

    async def upload_image(self, image_path: str, overwrite: bool = True) -> str:
        """
        上传图片到 ComfyUI 的 input 目录。

        Args:
            image_path: 本地图片路径
            overwrite: 是否覆盖已存在的文件

        Returns:
            ComfyUI 中的文件名
        """
        path = Path(image_path)
        filename = path.name

        async with httpx.AsyncClient(timeout=60) as client:
            with open(image_path, "rb") as f:
                resp = await client.post(
                    f"{self.base_url}/upload/image",
                    files={"image": (filename, f, "image/png")},
                    data={"overwrite": str(overwrite).lower()},
                )
            resp.raise_for_status()
            data = resp.json()
            return data.get("name", filename)
