"""请求模型定义"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DiagnoseImageRequest(BaseModel):
    """单图诊断请求"""

    image: Optional[str] = Field(
        None,
        description="Base64编码的图片",
    )
    image_url: Optional[str] = Field(
        None,
        description="图片URL",
    )
    profile: str = Field(
        "normal",
        description="配置模板: strict/normal/loose",
    )
    level: str = Field(
        "standard",
        description="检测级别: fast/standard/deep",
    )
    detectors: Optional[List[str]] = Field(
        None,
        description="指定检测器列表",
    )
    return_evidence: bool = Field(
        True,
        description="是否返回证据数据",
    )
    save_sample: bool = Field(
        False,
        description="是否保存样本",
    )


class BatchImageItem(BaseModel):
    """批量诊断中的单个图像项"""

    id: str = Field(..., description="图像ID")
    url: Optional[str] = Field(None, description="图片URL")
    base64: Optional[str] = Field(None, description="Base64编码的图片")
    path: Optional[str] = Field(None, description="本地文件路径")


class DiagnoseBatchRequest(BaseModel):
    """批量诊断请求"""

    images: List[BatchImageItem] = Field(
        ...,
        description="图像列表",
        min_length=1,
        max_length=100,
    )
    profile: str = Field(
        "normal",
        description="配置模板",
    )
    level: str = Field(
        "fast",
        description="检测级别",
    )
    detectors: Optional[List[str]] = Field(
        None,
        description="指定检测器列表",
    )
    callback_url: Optional[str] = Field(
        None,
        description="完成后回调URL",
    )


class UpdateConfigRequest(BaseModel):
    """更新配置请求"""

    profile: Optional[str] = Field(None, description="配置模板")
    detection_level: Optional[str] = Field(None, description="检测级别")
    parallel_detection: Optional[bool] = Field(None, description="是否并行检测")
    max_workers: Optional[int] = Field(None, description="最大工作线程数")
    custom_thresholds: Optional[Dict[str, float]] = Field(
        None,
        description="自定义阈值",
    )


class UpdateThresholdsRequest(BaseModel):
    """更新阈值请求"""

    blur_threshold: Optional[float] = Field(None, description="模糊检测阈值")
    brightness_min: Optional[float] = Field(None, description="最小亮度阈值")
    brightness_max: Optional[float] = Field(None, description="最大亮度阈值")
    contrast_min: Optional[float] = Field(None, description="最小对比度阈值")
    saturation_min: Optional[float] = Field(None, description="最小饱和度阈值")
    color_cast_threshold: Optional[float] = Field(None, description="偏色阈值")
    noise_threshold: Optional[float] = Field(None, description="噪声阈值")
    stripe_threshold: Optional[float] = Field(None, description="条纹阈值")

