"""pytest配置和fixtures"""

import numpy as np
import pytest
import cv2


@pytest.fixture
def sample_image():
    """生成标准测试图像"""
    # 创建一个有纹理的测试图像
    img = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    
    # 添加一些边缘和纹理
    cv2.rectangle(img, (100, 100), (300, 300), (255, 255, 255), 2)
    cv2.circle(img, (400, 200), 50, (0, 0, 255), -1)
    
    return img


@pytest.fixture
def blur_image():
    """生成模糊测试图像"""
    img = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    # 高斯模糊
    img = cv2.GaussianBlur(img, (31, 31), 10)
    return img


@pytest.fixture
def dark_image():
    """生成过暗测试图像"""
    img = np.random.randint(0, 15, (480, 640, 3), dtype=np.uint8)
    return img


@pytest.fixture
def bright_image():
    """生成过亮测试图像"""
    img = np.random.randint(240, 255, (480, 640, 3), dtype=np.uint8)
    return img


@pytest.fixture
def noisy_image():
    """生成噪声测试图像"""
    img = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    # 添加高斯噪声
    noise = np.random.normal(0, 30, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return img


@pytest.fixture
def black_image():
    """生成黑屏测试图像"""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def blue_screen_image():
    """生成蓝屏测试图像"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:, :, 0] = 200  # B通道
    img[:, :, 1] = 50   # G通道
    img[:, :, 2] = 50   # R通道
    return img


@pytest.fixture
def grayscale_image():
    """生成灰度测试图像"""
    gray = np.random.randint(50, 200, (480, 640), dtype=np.uint8)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def pipeline_config():
    """流水线配置"""
    return {
        "profile": "normal",
        "parallel_detection": True,
        "max_workers": 4,
        "blur_threshold": 100.0,
        "brightness_min": 20.0,
        "brightness_max": 235.0,
        "contrast_min": 30.0,
        "saturation_min": 10.0,
        "color_cast_threshold": 30.0,
        "noise_threshold": 15.0,
        "stripe_threshold": 0.3,
    }

