"""
阿里百练图片编辑服务

使用百练多模态 API（qwen-image-edit-plus）进行图片文字替换。
支持极端宽高比补边、结果裁剪、缩放回原图、去黑背景。
"""

import asyncio
import base64
import io
import logging
import uuid
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 百练多模态生成 API
BAILIAN_API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


class BailianImageService:
    """阿里百练图片编辑服务."""

    def __init__(self) -> None:
        self.api_key = settings.BAILIAN_API_KEY
        self.model = settings.BAILIAN_IMAGE_MODEL
        self.negative_prompt = (
            "jaggy, aliasing, pixelated, blurry, distorted text, "
            "garbled, watermark, low quality, artifacts, noise"
        )

    async def edit_image(
        self,
        image_path: str,
        target_text: str,
        output_dir: str | None = None,
    ) -> str | None:
        """图生图：替换图片中的文字.

        完整流程：
        1. 极端宽高比补透明边
        2. 调百练 API
        3. 下载结果并裁剪回原始比例
        4. 缩放到原图尺寸
        5. 参考原图去黑背景

        Args:
            image_path: 原始图片路径
            target_text: 目标文字
            output_dir: 输出目录

        Returns:
            结果图片本地路径，失败返回 None
        """
        t0 = asyncio.get_event_loop().time()
        logger.info("图生图开始 | 图片=%s | 目标文字=%s", Path(image_path).name, target_text[:50])

        try:
            img_path = Path(image_path)
            if not img_path.exists():
                logger.error("原始图片不存在: %s", image_path)
                return None

            with open(img_path, "rb") as f:
                image_bytes = f.read()

            # 构造英文 prompt
            prompt = (
                f"Replace the text in the image with '{target_text}'. "
                f"Keep the exact same font style, size, color, and position. "
                f"Do NOT change any other part of the image. "
                f"The output must be clean, sharp, and high quality."
            )

            # 补边：极端比例补透明像素
            padded_bytes, crop_box, orig_size = self._pad_image(image_bytes)

            b64 = base64.b64encode(padded_bytes).decode("utf-8")

            padded_img = Image.open(io.BytesIO(padded_bytes))
            logger.info(
                "调用百练 API | model=%s | 原始=%dx%d | 补后=%dx%d",
                self.model, orig_size[0], orig_size[1],
                padded_img.width, padded_img.height,
            )

            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": f"data:image/png;base64,{b64}"},
                                {"text": prompt},
                            ],
                        }
                    ]
                },
                "parameters": {
                    "n": 1,
                    "negative_prompt": self.negative_prompt,
                },
            }

            result_url = await self._call_bailian(payload)
            if result_url is None:
                return None

            # 下载百练结果
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(result_url)
                resp.raise_for_status()
                result_bytes = resp.content

            # 裁剪回原始比例
            if crop_box != (0, 0, orig_size[0], orig_size[1]):
                result_bytes = self._crop_result(result_bytes, crop_box)

            # 后处理：缩放 + 去黑背景
            result_bytes = self._post_process(result_bytes, orig_size, image_bytes)

            # 保存
            if output_dir is None:
                output_dir = str(img_path.parent / "results")
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            result_filename = f"result_{img_path.stem}_{uuid.uuid4().hex[:8]}.png"
            result_path = out_dir / result_filename

            with open(result_path, "wb") as f:
                f.write(result_bytes)

            elapsed = (asyncio.get_event_loop().time() - t0) * 1000
            logger.info(
                "图生图完成 | 输出=%s | 尺寸=%dx%d | 耗时=%.0fms",
                result_filename, orig_size[0], orig_size[1], elapsed,
            )
            return str(result_path)

        except Exception as e:
            logger.error("图生图失败 | 图片=%s | 错误=%s", image_path, e)
            return None

    # ---- 内部方法 ----

    @staticmethod
    def _pad_image(image_bytes: bytes, max_ratio: float = 4.0) -> tuple[bytes, tuple, tuple]:
        """极端宽高比补透明像素."""
        img = Image.open(io.BytesIO(image_bytes))
        ow, oh = img.size
        ratio = ow / oh if ow >= oh else oh / ow

        if ratio <= max_ratio:
            return image_bytes, (0, 0, ow, oh), (ow, oh)

        if ow >= oh:
            new_h = max(int(ow / max_ratio), oh)
            pad_top = (new_h - oh) // 2
            canvas = Image.new("RGBA", (ow, new_h), (0, 0, 0, 0))
            canvas.paste(img.convert("RGBA"), (0, pad_top))
            crop_box = (0, pad_top, ow, pad_top + oh)
        else:
            new_w = max(int(oh / max_ratio), ow)
            pad_left = (new_w - ow) // 2
            canvas = Image.new("RGBA", (new_w, oh), (0, 0, 0, 0))
            canvas.paste(img.convert("RGBA"), (pad_left, 0))
            crop_box = (pad_left, 0, pad_left + ow, oh)

        logger.info("图片补边 | %dx%d -> %dx%d", ow, oh, canvas.width, canvas.height)
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        return buf.getvalue(), crop_box, (ow, oh)

    @staticmethod
    def _crop_result(image_bytes: bytes, crop_box: tuple) -> bytes:
        """裁剪百练结果回原始比例."""
        img = Image.open(io.BytesIO(image_bytes))
        x, y, w, h = crop_box
        scale_x = img.width / max(w + x, 1)
        scale_y = img.height / max(h + y, 1)
        sx, sy = int(x * scale_x), int(y * scale_y)
        sw, sh = int(w * scale_x), int(h * scale_y)
        cropped = img.crop((sx, sy, sx + sw, sy + sh))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _post_process(result_bytes: bytes, orig_size: tuple, orig_image_bytes: bytes) -> bytes:
        """后处理：缩放到原图 + 去黑背景."""
        img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        ow, oh = orig_size

        # 缩放
        if img.size != (ow, oh):
            img = img.resize((ow, oh), Image.LANCZOS)

        # 去黑背景
        orig_img = Image.open(io.BytesIO(orig_image_bytes)).convert("RGBA")
        orig_alpha = np.array(orig_img.split()[3])
        result_arr = np.array(img)

        # 原图透明区域，结果也透明
        transparent_mask = orig_alpha < 10
        result_arr[transparent_mask, 3] = 0

        # 纯黑且原图也透明
        black_mask = (
            (result_arr[:, :, 0] < 15)
            & (result_arr[:, :, 1] < 15)
            & (result_arr[:, :, 2] < 15)
        )
        result_arr[black_mask & transparent_mask, 3] = 0

        result_img = Image.fromarray(result_arr, "RGBA")
        buf = io.BytesIO()
        result_img.save(buf, format="PNG")
        return buf.getvalue()

    async def _call_bailian(self, payload: dict) -> Optional[str]:
        """调用百练 API，返回图片 URL."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(BAILIAN_API, json=payload, headers=headers)

            if resp.status_code != 200:
                logger.error("百练 API 错误 | status=%d | body=%s", resp.status_code, resp.text[:500])
                return None

            data = resp.json()

            # 同步返回: output.choices[].message.content[].image
            choices = data.get("output", {}).get("choices", [])
            if choices:
                contents = choices[0].get("message", {}).get("content", [])
                for c in contents:
                    if c.get("image"):
                        return c["image"]

            # 旧格式: output.results[].url
            results = data.get("output", {}).get("results", [])
            if results and results[0].get("url"):
                return results[0]["url"]

            # 异步任务
            task_id = data.get("output", {}).get("task_id")
            if task_id:
                return await self._poll_task(client, task_id, headers)

            logger.error("百练返回格式无法解析: %s", str(data)[:500])
            return None

    async def _poll_task(self, client: httpx.AsyncClient, task_id: str, headers: dict) -> Optional[str]:
        """轮询异步任务."""
        poll_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

        for i in range(60):
            await asyncio.sleep(3)
            resp = await client.get(poll_url, headers=headers)
            if resp.status_code != 200:
                continue

            data = resp.json()
            status = data.get("output", {}).get("task_status", "")

            if status == "SUCCEEDED":
                choices = data.get("output", {}).get("choices", [])
                if choices:
                    for c in choices[0].get("message", {}).get("content", []):
                        if c.get("image"):
                            return c["image"]
                results = data.get("output", {}).get("results", [])
                if results:
                    return results[0].get("url")
                return None

            elif status == "FAILED":
                logger.error("异步任务失败: %s", data.get("output", {}).get("message", ""))
                return None

            logger.info("轮询 %d | status=%s", i + 1, status)

        logger.error("异步任务超时")
        return None


# 全局单例
_service: BailianImageService | None = None


def get_bailian_service() -> BailianImageService:
    global _service
    if _service is None:
        _service = BailianImageService()
    return _service
