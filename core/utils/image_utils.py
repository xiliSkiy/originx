"""图像处理工具函数"""

import base64
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np
import requests


def load_image(
    source: Union[str, Path, np.ndarray],
    max_size: Optional[int] = None,
) -> Optional[np.ndarray]:
    """
    加载图像

    Args:
        source: 图像来源（文件路径、URL、Base64字符串或numpy数组）
        max_size: 最大尺寸（宽或高），超过则等比缩放

    Returns:
        np.ndarray: BGR格式图像，加载失败返回None
    """
    image = None

    if isinstance(source, np.ndarray):
        image = source
    elif isinstance(source, (str, Path)):
        source_str = str(source)

        # 判断是URL还是文件路径
        if source_str.startswith(("http://", "https://")):
            image = load_image_from_url(source_str)
        elif source_str.startswith("data:image"):
            # data URI 格式
            image = load_image_from_base64(source_str.split(",", 1)[1])
        elif len(source_str) > 500 and not Path(source_str).exists():
            # 可能是Base64字符串
            image = load_image_from_base64(source_str)
        else:
            # 文件路径
            image = cv2.imread(source_str, cv2.IMREAD_COLOR)

    if image is not None and max_size is not None:
        image = resize_image(image, max_size=max_size)

    return image


def load_image_from_base64(base64_string: str) -> Optional[np.ndarray]:
    """
    从Base64字符串加载图像

    Args:
        base64_string: Base64编码的图像字符串

    Returns:
        np.ndarray: BGR格式图像，加载失败返回None
    """
    try:
        # 移除可能的前缀
        if "," in base64_string:
            base64_string = base64_string.split(",", 1)[1]

        image_bytes = base64.b64decode(base64_string)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return image
    except Exception:
        return None


def load_image_from_url(
    url: str,
    timeout: int = 10,
) -> Optional[np.ndarray]:
    """
    从URL加载图像

    Args:
        url: 图像URL
        timeout: 请求超时时间（秒）

    Returns:
        np.ndarray: BGR格式图像，加载失败返回None
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        image_array = np.frombuffer(response.content, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return image
    except Exception:
        return None


def resize_image(
    image: np.ndarray,
    target_size: Optional[Tuple[int, int]] = None,
    max_size: Optional[int] = None,
    interpolation: int = cv2.INTER_AREA,
) -> np.ndarray:
    """
    调整图像尺寸

    Args:
        image: 输入图像
        target_size: 目标尺寸 (width, height)
        max_size: 最大尺寸（宽或高），等比缩放
        interpolation: 插值方法

    Returns:
        np.ndarray: 调整后的图像
    """
    if image is None or image.size == 0:
        return image

    h, w = image.shape[:2]

    if target_size is not None:
        return cv2.resize(image, target_size, interpolation=interpolation)

    if max_size is not None:
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    return image


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    转换为灰度图

    Args:
        image: BGR格式图像

    Returns:
        np.ndarray: 灰度图像
    """
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def to_hsv(image: np.ndarray) -> np.ndarray:
    """
    转换为HSV色彩空间

    Args:
        image: BGR格式图像

    Returns:
        np.ndarray: HSV图像
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)


def calculate_histogram(
    image: np.ndarray,
    channel: int = 0,
    bins: int = 256,
    normalize: bool = True,
) -> np.ndarray:
    """
    计算直方图

    Args:
        image: 输入图像
        channel: 通道索引
        bins: 直方图bin数量
        normalize: 是否归一化

    Returns:
        np.ndarray: 直方图
    """
    if len(image.shape) == 2:
        hist = cv2.calcHist([image], [0], None, [bins], [0, 256])
    else:
        hist = cv2.calcHist([image], [channel], None, [bins], [0, 256])

    if normalize:
        hist = hist / hist.sum()

    return hist.flatten()


def normalize_image(
    image: np.ndarray,
    target_range: Tuple[float, float] = (0, 1),
) -> np.ndarray:
    """
    归一化图像

    Args:
        image: 输入图像
        target_range: 目标范围

    Returns:
        np.ndarray: 归一化后的图像
    """
    min_val, max_val = target_range
    image_float = image.astype(np.float32)
    image_normalized = cv2.normalize(
        image_float, None, min_val, max_val, cv2.NORM_MINMAX
    )
    return image_normalized


def get_image_info(image: np.ndarray) -> dict:
    """
    获取图像信息

    Args:
        image: 输入图像

    Returns:
        dict: 图像信息
    """
    if image is None:
        return {"valid": False}

    h, w = image.shape[:2]
    channels = image.shape[2] if len(image.shape) > 2 else 1

    return {
        "valid": True,
        "width": w,
        "height": h,
        "channels": channels,
        "dtype": str(image.dtype),
        "size_bytes": image.nbytes,
    }


def crop_image(
    image: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
) -> np.ndarray:
    """
    裁剪图像

    Args:
        image: 输入图像
        x: 左上角x坐标
        y: 左上角y坐标
        width: 宽度
        height: 高度

    Returns:
        np.ndarray: 裁剪后的图像
    """
    h, w = image.shape[:2]
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    width = min(width, w - x)
    height = min(height, h - y)

    return image[y : y + height, x : x + width]


def create_thumbnail(
    image: np.ndarray,
    size: Tuple[int, int] = (320, 240),
) -> np.ndarray:
    """
    创建缩略图

    Args:
        image: 输入图像
        size: 缩略图尺寸 (width, height)

    Returns:
        np.ndarray: 缩略图
    """
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA)

