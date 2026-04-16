"""
Excel 处理服务

负责读取/写入 Excel 文件，提取图片和文本。
"""

import io
import uuid
import logging
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XlImage
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ExcelItem:
    """Excel 中的一行数据"""

    def __init__(self, row_index: int, image_path: str, target_text: str):
        self.row_index = row_index
        self.image_path = image_path
        self.target_text = target_text


class ExcelProcessor:
    """Excel 文件处理器"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.task_dir = settings.UPLOAD_DIR / task_id
        self.task_dir.mkdir(parents=True, exist_ok=True)

    def read_excel(self, filepath: str | Path) -> list[ExcelItem]:
        """
        读取 Excel 文件，提取图片和目标文本。

        Args:
            filepath: Excel 文件路径

        Returns:
            ExcelItem 列表

        处理逻辑：
        1. 从第一列提取嵌入的图片
        2. 从第二列读取目标替换文本
        3. 将图片保存到任务目录
        """
        wb = load_workbook(filepath)
        ws = wb.active
        items = []

        # 提取所有嵌入图片，建立 (row, col) -> 图片文件路径 的映射
        image_map = self._extract_images(ws)

        for row_idx in range(2, ws.max_row + 1):
            # 读取第二列目标文本
            target_text_cell = ws.cell(row=row_idx, column=2)
            target_text = str(target_text_cell.value).strip() if target_text_cell.value else ""

            if not target_text:
                logger.warning(f"Row {row_idx}: 跳过，目标文本为空")
                continue

            # 查找该行第一列对应的图片
            image_path = image_map.get(row_idx)
            if not image_path:
                logger.warning(f"Row {row_idx}: 跳过，未找到图片")
                continue

            items.append(ExcelItem(
                row_index=row_idx - 2,  # 0-based 索引
                image_path=image_path,
                target_text=target_text,
            ))

        wb.close()
        logger.info(f"Task {self.task_id}: 从 Excel 提取 {len(items)} 个处理项")
        return items

    def _extract_images(self, ws) -> dict[int, str]:
        """
        从工作表中提取所有图片。

        Returns:
            {row_number: image_file_path} 映射
        """
        image_map = {}

        for idx, img in enumerate(ws._images):
            # openpyxl 的 _images 中图片没有直接的行列信息，
            # 需要通过锚点（anchor）来推算
            try:
                # 获取图片的锚点定位
                anchor = img.anchor
                if hasattr(anchor, '_from'):
                    # TwoCellAnchor 或 OneCellAnchor
                    row = anchor._from.row + 1  # openpyxl 行号 0-based，转 1-based
                elif hasattr(anchor, 'row'):
                    row = anchor.row + 1
                else:
                    # 如果无法定位，按图片顺序依次分配
                    row = idx + 2  # 跳过表头
                    logger.warning(f"Image {idx}: 无法定位行号，默认分配到 row {row}")
            except Exception:
                row = idx + 2
                logger.warning(f"Image {idx}: 定位异常，默认分配到 row {row}")

            # 保存图片到任务目录
            img_filename = f"original_{row}.png"
            img_path = self.task_dir / img_filename

            # 将图片数据转为 PIL Image 再保存为 PNG
            image_data = img._data()
            pil_img = Image.open(io.BytesIO(image_data))
            pil_img.save(str(img_path), "PNG")

            image_map[row] = str(img_path)
            logger.debug(f"Image extracted: row {row} -> {img_path}")

        return image_map

    def write_results(
        self,
        source_filepath: str | Path,
        results: dict[int, str],
        output_filepath: str | Path | None = None,
    ) -> str:
        """
        将处理结果写回 Excel 第三列。

        Args:
            source_filepath: 原始 Excel 路径
            results: {row_index(0-based): result_image_path} 映射
            output_filepath: 输出文件路径（默认覆盖原文件）

        Returns:
            结果文件路径
        """
        source_filepath = Path(source_filepath)
        output_filepath = Path(output_filepath) if output_filepath else source_filepath

        wb = load_workbook(source_filepath)
        ws = wb.active

        for row_idx_0, result_path in results.items():
            excel_row = row_idx_0 + 2  # 转回 Excel 行号（跳过表头）
            if not Path(result_path).exists():
                logger.warning(f"Row {excel_row}: 结果图片不存在 {result_path}")
                continue

            # 将处理后的图片插入第三列
            img = XlImage(result_path)
            # 调整图片大小以适应单元格
            img.width = min(img.width, 200)
            img.height = min(img.height, 200)
            ws.add_image(img, f"C{excel_row}")

        wb.save(str(output_filepath))
        wb.close()
        logger.info(f"Task {self.task_id}: 结果已写入 {output_filepath}")
        return str(output_filepath)
