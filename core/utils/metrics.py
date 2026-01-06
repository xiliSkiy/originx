"""图像质量指标计算"""

from typing import Tuple

import cv2
import numpy as np


def calculate_laplacian_variance(image: np.ndarray) -> float:
    """
    计算拉普拉斯方差（用于模糊检测）

    Args:
        image: 输入图像（BGR或灰度）

    Returns:
        float: 拉普拉斯方差，值越大越清晰
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def calculate_gradient_magnitude(image: np.ndarray) -> Tuple[float, float]:
    """
    计算梯度幅值（用于模糊检测）

    Args:
        image: 输入图像（BGR或灰度）

    Returns:
        Tuple[float, float]: (梯度均值, 梯度标准差)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Sobel梯度
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)

    return float(gradient_magnitude.mean()), float(gradient_magnitude.std())


def calculate_brenner_gradient(image: np.ndarray) -> float:
    """
    计算Brenner梯度（用于模糊检测）

    Args:
        image: 输入图像（BGR或灰度）

    Returns:
        float: Brenner梯度值
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    diff = gray[:, 2:].astype(float) - gray[:, :-2].astype(float)
    return float(np.mean(diff**2))


def calculate_brightness(image: np.ndarray) -> Tuple[float, float, float]:
    """
    计算亮度指标

    Args:
        image: 输入图像（BGR格式）

    Returns:
        Tuple[float, float, float]: (平均亮度, 最小亮度百分位, 最大亮度百分位)
    """
    if len(image.shape) == 3:
        # 转换为灰度或使用亮度通道
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    mean_brightness = float(gray.mean())
    p5 = float(np.percentile(gray, 5))  # 5%分位数
    p95 = float(np.percentile(gray, 95))  # 95%分位数

    return mean_brightness, p5, p95


def calculate_contrast(image: np.ndarray) -> Tuple[float, float]:
    """
    计算对比度

    Args:
        image: 输入图像（BGR或灰度）

    Returns:
        Tuple[float, float]: (标准差对比度, 动态范围)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    std_contrast = float(gray.std())
    dynamic_range = float(gray.max()) - float(gray.min())

    return std_contrast, dynamic_range


def calculate_saturation(image: np.ndarray) -> Tuple[float, float]:
    """
    计算饱和度

    Args:
        image: 输入图像（BGR格式）

    Returns:
        Tuple[float, float]: (平均饱和度, 饱和度标准差)
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]

    mean_saturation = float(saturation.mean())
    std_saturation = float(saturation.std())

    return mean_saturation, std_saturation


def calculate_color_cast(image: np.ndarray) -> Tuple[float, float, float, float]:
    """
    计算偏色程度

    Args:
        image: 输入图像（BGR格式）

    Returns:
        Tuple[float, float, float, float]: (B通道均值, G通道均值, R通道均值, 最大偏差)
    """
    b_mean = float(image[:, :, 0].mean())
    g_mean = float(image[:, :, 1].mean())
    r_mean = float(image[:, :, 2].mean())

    # 计算各通道与均值的偏差
    avg = (b_mean + g_mean + r_mean) / 3
    max_deviation = max(abs(b_mean - avg), abs(g_mean - avg), abs(r_mean - avg))

    return b_mean, g_mean, r_mean, max_deviation


def estimate_noise(image: np.ndarray, method: str = "laplacian") -> float:
    """
    估计图像噪声水平

    Args:
        image: 输入图像
        method: 估计方法 ("laplacian" 或 "median")

    Returns:
        float: 噪声估计值
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    if method == "laplacian":
        # 使用拉普拉斯算子估计噪声
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        # 噪声估计（使用MAD - Median Absolute Deviation）
        sigma = np.median(np.abs(laplacian)) / 0.6745
        return float(sigma)

    elif method == "median":
        # 使用中值滤波残差估计噪声
        filtered = cv2.medianBlur(gray, 5)
        residual = gray.astype(float) - filtered.astype(float)
        return float(np.std(residual))

    return 0.0


def calculate_edge_density(image: np.ndarray) -> float:
    """
    计算边缘密度

    Args:
        image: 输入图像

    Returns:
        float: 边缘像素占比
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.count_nonzero(edges) / edges.size

    return float(edge_density)


def calculate_entropy(image: np.ndarray) -> float:
    """
    计算图像熵

    Args:
        image: 输入图像

    Returns:
        float: 图像熵值
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # 计算直方图
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()

    # 计算熵
    hist = hist[hist > 0]  # 移除零值
    entropy = -np.sum(hist * np.log2(hist))

    return float(entropy)


def detect_stripe_pattern(image: np.ndarray) -> Tuple[float, bool, str]:
    """
    检测条纹图案

    Args:
        image: 输入图像

    Returns:
        Tuple[float, bool, str]: (条纹强度, 是否有条纹, 条纹方向)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # FFT分析
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)

    # 归一化
    magnitude = magnitude / magnitude.max()

    h, w = magnitude.shape
    cy, cx = h // 2, w // 2

    # 分析水平和垂直方向的能量
    horizontal_energy = magnitude[cy - 2 : cy + 2, :].mean()
    vertical_energy = magnitude[:, cx - 2 : cx + 2].mean()

    # 排除中心区域后计算
    margin = min(h, w) // 10
    horizontal_stripe = magnitude[cy - 2 : cy + 2, margin:-margin].mean()
    vertical_stripe = magnitude[margin:-margin, cx - 2 : cx + 2].mean()

    # 判断条纹强度
    stripe_strength = max(horizontal_stripe, vertical_stripe)

    # 确定方向
    direction = "none"
    has_stripe = stripe_strength > 0.1

    if has_stripe:
        if horizontal_stripe > vertical_stripe * 1.5:
            direction = "horizontal"
        elif vertical_stripe > horizontal_stripe * 1.5:
            direction = "vertical"
        else:
            direction = "both"

    return float(stripe_strength), has_stripe, direction

