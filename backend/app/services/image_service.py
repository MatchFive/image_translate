"""
图片处理服务

使用 OpenCV 处理透明背景、缩放等操作。
"""

import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def has_transparency(image: Image.Image) -> bool:
    """
    检测图片是否包含透明通道（Alpha Channel）。

    Args:
        image: PIL Image 对象

    Returns:
        是否包含透明像素
    """
    if image.mode != "RGBA":
        return False

    # 检查 alpha 通道是否存在非 255（非完全不透明）的像素
    alpha = np.array(image.split()[-1])
    return bool(np.any(alpha < 255))


def process_transparency(image: Image.Image, reference: Image.Image) -> Image.Image:
    """
    处理透明背景。

    如果参考图（原图）有透明背景，则：
    1. 将结果图转为 RGBA
    2. 从原图提取 alpha 通道
    3. 应用 alpha 通道到结果图

    Args:
        image: 处理后的图片
        reference: 原始参考图片

    Returns:
        处理后的 PIL Image（RGBA 模式）
    """
    if not has_transparency(reference):
        logger.debug("原图无透明背景，跳过透明处理")
        return image

    logger.info("检测到透明背景，正在处理...")

    # 确保两张图片尺寸一致
    ref_rgba = reference.convert("RGBA")
    result_rgba = image.convert("RGBA").resize(ref_rgba.size, Image.LANCZOS)

    # 从原图提取 alpha 通道
    ref_array = np.array(ref_rgba)
    result_array = np.array(result_rgba)

    # 应用原图的 alpha 通道到结果
    result_array[:, :, 3] = ref_array[:, :, 3]

    return Image.fromarray(result_array, "RGBA")


def resize_to_match(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """
    将图片缩放到目标尺寸。

    Args:
        image: 源图片
        target_size: 目标尺寸 (width, height)

    Returns:
        缩放后的 PIL Image
    """
    current_size = image.size
    if current_size == target_size:
        return image

    logger.info(f"缩放图片: {current_size} -> {target_size}")
    return image.resize(target_size, Image.LANCZOS)


def process_image(
    result_image: Image.Image,
    original_image: Image.Image,
    output_path: str,
) -> str:
    """
    图片后处理管线。

    1. 检测并处理透明背景
    2. 缩放到原始尺寸
    3. 保存到指定路径

    Args:
        result_image: ComfyUI 生成的结果图片
        original_image: 原始上传图片
        output_path: 输出文件路径

    Returns:
        处理后的图片路径
    """
    # Step 1: 处理透明背景
    processed = process_transparency(result_image, original_image)

    # Step 2: 缩放到原始尺寸
    processed = resize_to_match(processed, original_image.size)

    # Step 3: 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed.save(str(output_path), "PNG")

    logger.info(f"图片处理完成，保存到 {output_path}")
    return str(output_path)


def detect_text_regions(image: Image.Image) -> list[dict]:
    """
    使用 OpenCV 检测图片中的文字区域。

    这是一个辅助方法，可用于未来扩展（如局部重绘）。

    Args:
        image: PIL Image

    Returns:
        文字区域列表 [{"bbox": [x, y, w, h], "confidence": float}]
    """
    import numpy as np

    img_array = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # 使用 MSER 或简单的边缘检测
    # 这里用简单的阈值方法做示例
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # 过滤太小的区域
        if w > 10 and h > 10:
            regions.append({
                "bbox": [int(x), int(y), int(w), int(h)],
            })

    return regions
