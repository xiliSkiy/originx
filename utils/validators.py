"""验证工具"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


SUPPORTED_IMAGE_FORMATS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
}


def validate_image_format(file_path: str) -> Tuple[bool, str]:
    """
    验证图像格式

    Args:
        file_path: 文件路径

    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    path = Path(file_path)

    if not path.exists():
        return False, f"文件不存在: {file_path}"

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        return False, f"不支持的图像格式: {suffix}"

    return True, ""


def validate_image_data(image: np.ndarray) -> Tuple[bool, str]:
    """
    验证图像数据

    Args:
        image: 图像数组

    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    if image is None:
        return False, "图像数据为空"

    if not isinstance(image, np.ndarray):
        return False, "图像数据类型错误"

    if image.size == 0:
        return False, "图像数据为空"

    if len(image.shape) < 2:
        return False, "图像维度错误"

    return True, ""


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证配置

    Args:
        config: 配置字典

    Returns:
        Tuple[bool, List[str]]: (是否有效, 错误列表)
    """
    errors = []

    # 验证profile
    profile = config.get("profile", "normal")
    if profile not in ["strict", "normal", "loose"]:
        errors.append(f"无效的配置模板: {profile}")

    # 验证detection_level
    level = config.get("detection_level", "standard")
    if level not in ["fast", "standard", "deep"]:
        errors.append(f"无效的检测级别: {level}")

    # 验证max_workers
    max_workers = config.get("max_workers", 4)
    if not isinstance(max_workers, int) or max_workers < 1:
        errors.append(f"无效的工作线程数: {max_workers}")

    # 验证阈值
    custom_thresholds = config.get("custom_thresholds", {})
    if custom_thresholds:
        for key, value in custom_thresholds.items():
            if not isinstance(value, (int, float)):
                errors.append(f"无效的阈值类型: {key}={value}")
            elif value < 0:
                errors.append(f"阈值不能为负数: {key}={value}")

    return len(errors) == 0, errors


def validate_detection_request(
    image: Optional[np.ndarray] = None,
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    验证诊断请求

    Args:
        image: 图像数组
        image_path: 图像路径
        image_url: 图像URL
        image_base64: Base64编码

    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    # 至少提供一种图像来源
    sources = [image, image_path, image_url, image_base64]
    provided = [s for s in sources if s is not None]

    if len(provided) == 0:
        return False, "请提供图像（file/path/url/base64）"

    if len(provided) > 1:
        return False, "只能提供一种图像来源"

    # 验证具体来源
    if image is not None:
        return validate_image_data(image)

    if image_path is not None:
        return validate_image_format(image_path)

    if image_url is not None:
        if not image_url.startswith(("http://", "https://")):
            return False, "无效的图像URL"

    if image_base64 is not None:
        if len(image_base64) < 100:
            return False, "无效的Base64编码"

    return True, ""

