"""诊断服务"""

from typing import Any, Dict, List, Optional

import numpy as np

from config import AppConfig, get_config
from core import DiagnosisPipeline, DiagnosisResult, DetectionLevel
from core.utils.image_utils import load_image


class DiagnosisService:
    """
    诊断服务

    封装诊断流程，提供便捷的诊断接口
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化诊断服务

        Args:
            config: 应用配置，None则使用全局配置
        """
        self.config = config or get_config()
        self._init_pipeline()

    def _init_pipeline(self) -> None:
        """初始化诊断流水线"""
        threshold_config = self.config.get_threshold_dict()
        threshold_config["profile"] = self.config.profile
        threshold_config["parallel_detection"] = self.config.parallel_detection
        threshold_config["max_workers"] = self.config.max_workers

        self.pipeline = DiagnosisPipeline(threshold_config)

    def diagnose_image(
        self,
        image: np.ndarray,
        level: str = "standard",
        detectors: Optional[List[str]] = None,
        image_id: str = "",
        image_path: str = "",
    ) -> DiagnosisResult:
        """
        诊断单张图像

        Args:
            image: BGR格式图像
            level: 检测级别 (fast/standard/deep)
            detectors: 指定检测器列表
            image_id: 图像ID
            image_path: 图像路径

        Returns:
            DiagnosisResult: 诊断结果
        """
        detection_level = DetectionLevel.from_string(level)

        return self.pipeline.diagnose(
            image=image,
            level=detection_level,
            detectors=detectors,
            image_id=image_id,
            image_path=image_path,
        )

    def diagnose_file(
        self,
        file_path: str,
        level: str = "standard",
        detectors: Optional[List[str]] = None,
    ) -> DiagnosisResult:
        """
        诊断图像文件

        Args:
            file_path: 图像文件路径
            level: 检测级别
            detectors: 指定检测器列表

        Returns:
            DiagnosisResult: 诊断结果
        """
        image = load_image(file_path)

        if image is None:
            raise ValueError(f"无法加载图像: {file_path}")

        return self.diagnose_image(
            image=image,
            level=level,
            detectors=detectors,
            image_path=file_path,
        )

    def diagnose_batch(
        self,
        images: List[Dict[str, Any]],
        level: str = "fast",
        detectors: Optional[List[str]] = None,
    ) -> List[DiagnosisResult]:
        """
        批量诊断

        Args:
            images: 图像列表，每个元素包含 image/path/url 等
            level: 检测级别
            detectors: 指定检测器列表

        Returns:
            List[DiagnosisResult]: 诊断结果列表
        """
        detection_level = DetectionLevel.from_string(level)
        results = []

        for item in images:
            image = None
            image_id = item.get("id", "")
            image_path = item.get("path", "")

            if "image" in item:
                image = item["image"]
            elif "path" in item:
                image = load_image(item["path"])
            elif "url" in item:
                from core.utils.image_utils import load_image_from_url
                image = load_image_from_url(item["url"])
            elif "base64" in item:
                from core.utils.image_utils import load_image_from_base64
                image = load_image_from_base64(item["base64"])

            if image is not None:
                result = self.pipeline.diagnose(
                    image=image,
                    level=detection_level,
                    detectors=detectors,
                    image_id=image_id,
                    image_path=image_path,
                )
                results.append(result)

        return results

    def reload_config(self, config: Optional[AppConfig] = None) -> None:
        """重新加载配置"""
        self.config = config or get_config()
        self._init_pipeline()


# 全局服务实例
_service: Optional[DiagnosisService] = None


def get_diagnosis_service() -> DiagnosisService:
    """获取全局诊断服务实例"""
    global _service
    if _service is None:
        _service = DiagnosisService()
    return _service

