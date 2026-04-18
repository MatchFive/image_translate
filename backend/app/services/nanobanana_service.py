"""
Nano Banana 图片编辑服务

使用 OpenAI 兼容格式的 /v1/images/edits 接口进行图片文字替换。
适用于各类第三方 API 代理或自建服务。
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


class NanoBananaService:
    """Nano Banana 图片编辑服务 — OpenAI 兼容 images/edits 接口."""

    def __init__(self) -> None:
        self.base_url = settings.NANO_BANANA_BASE_URL
        self.api_key = settings.NANO_BANANA_API_KEY
        self.model = settings.NANO_BANANA_MODEL

    async def edit_image(
        self,
        image_path: str,
        target_text: str,
        output_dir: str | None = None,
    ) -> str | None:
        """图生图：替换图片中的文字.

        Args:
            image_path: 原始图片路径
            target_text: 目标文字
            output_dir: 输出目录

        Returns:
            结果图片本地路径，失败返回 None
        """
        t0 = asyncio.get_event_loop().time()
        logger.info("NanoBanana 图生图开始 | 图片=%s | 目标=%s", Path(image_path).name, target_text[:50])

        try:
            img_path = Path(image_path)
            if not img_path.exists():
                logger.error("原始图片不存在: %s", image_path)
                return None

            with open(img_path, "rb") as f:
                image_bytes = f.read()

            prompt = (
                f"Replace the text in the image with '{target_text}'. "
                f"Keep the exact same font style, size, color, and position. "
                f"Do NOT change any other part of the image. "
                f"The output must be clean, sharp, and high quality."
            )

            # 补边：极端比例补透明像素
            padded_bytes, crop_box, orig_size = _pad_image(image_bytes)

            padded_img = Image.open(io.BytesIO(padded_bytes))
            logger.info(
                "NanoBanana API | model=%s | 原始=%dx%d | 补后=%dx%d",
                self.model, orig_size[0], orig_size[1],
                padded_img.width, padded_img.height,
            )

            # 调用 OpenAI 兼容 images/edits 接口
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )

            # 用 io.BytesIO 包装 bytes，带文件名
            img_file = io.BytesIO(padded_bytes)
            img_file.name = "image.png"

            response = await client.images.edit(
                model=self.model,
                image=img_file,
                prompt=prompt,
                n=1,
            )

            if not response.data or len(response.data) == 0:
                logger.error("NanoBanana 返回空结果")
                return None

            # 获取结果
            image_result = response.data[0]
            result_url = getattr(image_result, "url", None)
            result_b64 = getattr(image_result, "b64_json", None)

            if result_url:
                async with httpx.AsyncClient(timeout=120) as http_client:
                    resp = await http_client.get(result_url)
                    resp.raise_for_status()
                    result_bytes = resp.content
            elif result_b64:
                result_bytes = base64.b64decode(result_b64)
            else:
                logger.error("NanoBanana 返回结果无 URL 也无 b64_json")
                return None

            # 裁剪回原始比例
            if crop_box != (0, 0, orig_size[0], orig_size[1]):
                result_bytes = _crop_result(result_bytes, crop_box)

            # 后处理：缩放 + 去黑背景
            result_bytes = _post_process(result_bytes, orig_size, image_bytes)

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
                "NanoBanana 完成 | 输出=%s | 尺寸=%dx%d | 耗时=%.0fms",
                result_filename, orig_size[0], orig_size[1], elapsed,
            )
            return str(result_path)

        except Exception as e:
            logger.error("NanoBanana 失败 | 图片=%s | 错误=%s", image_path, e)
            return None


# ---- 共享工具函数 ----

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


def _crop_result(image_bytes: bytes, crop_box: tuple) -> bytes:
    """裁剪结果回原始比例."""
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


def _post_process(result_bytes: bytes, orig_size: tuple, orig_image_bytes: bytes) -> bytes:
    """后处理：缩放 + 去黑背景."""
    img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    ow, oh = orig_size

    if img.size != (ow, oh):
        img = img.resize((ow, oh), Image.LANCZOS)

    orig_img = Image.open(io.BytesIO(orig_image_bytes)).convert("RGBA")
    orig_alpha = np.array(orig_img.split()[3])
    result_arr = np.array(img)

    transparent_mask = orig_alpha < 10
    result_arr[transparent_mask, 3] = 0

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


# 全局单例
_service: NanoBananaService | None = None


def get_nanobanana_service() -> NanoBananaService:
    global _service
    if _service is None:
        _service = NanoBananaService()
    return _service
