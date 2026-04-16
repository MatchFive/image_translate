"""
OCR 验证服务

使用 rapidocr-onnxruntime 进行本地文字识别，验证替换结果。
"""

import logging
from difflib import SequenceMatcher

from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# OCR 引擎（延迟初始化）
_ocr_engine = None


def get_ocr_engine():
    """获取 OCR 引擎单例"""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR 引擎初始化成功")
        except ImportError:
            logger.warning("rapidocr-onnxruntime 未安装，OCR 验证将被跳过")
            _ocr_engine = None
    return _ocr_engine


def perform_ocr(image: Image.Image) -> str:
    """
    对图片执行 OCR 识别。

    Args:
        image: PIL Image 对象

    Returns:
        识别出的文本（多行合并）
    """
    engine = get_ocr_engine()
    if engine is None:
        return ""

    import numpy as np
    img_array = np.array(image)
    result, _ = engine(img_array)

    if not result:
        return ""

    # result 是 list of [text, confidence, bbox]
    texts = [item[0] for item in result]
    return "".join(texts)


def calculate_similarity(text1: str, text2: str) -> float:
    """
    计算两段文本的相似度。

    使用 SequenceMatcher 计算相似比率，
    并做简单的空白字符清理。

    Args:
        text1: 文本1（OCR 结果）
        text2: 文本2（目标文本）

    Returns:
        0.0 ~ 1.0 的相似度分数
    """
    # 清理空白字符
    clean1 = text1.replace(" ", "").replace("\n", "").strip()
    clean2 = text2.replace(" ", "").replace("\n", "").strip()

    if not clean1 or not clean2:
        return 0.0

    return SequenceMatcher(None, clean1, clean2).ratio()


def verify_text(
    image: Image.Image,
    target_text: str,
    threshold: float | None = None,
) -> tuple[bool, str, float]:
    """
    验证图片中的文字是否匹配目标文本。

    Args:
        image: 待验证的 PIL Image
        target_text: 目标文本
        threshold: 匹配阈值（默认从配置读取）

    Returns:
        (is_match, ocr_text, score) 三元组
    """
    if threshold is None:
        threshold = settings.OCR_MATCH_THRESHOLD

    ocr_text = perform_ocr(image)
    if not ocr_text:
        logger.warning("OCR 未识别到任何文本")
        return False, "", 0.0

    score = calculate_similarity(ocr_text, target_text)
    is_match = score >= threshold

    logger.info(
        f"OCR 验证: target='{target_text}', ocr='{ocr_text}', "
        f"score={score:.2f}, match={is_match}"
    )

    return is_match, ocr_text, score
