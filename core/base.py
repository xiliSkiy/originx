"""检测器基类定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class Severity(Enum):
    """异常严重程度"""

    NORMAL = "normal"  # 正常
    INFO = "info"  # 提示
    WARNING = "warning"  # 警告
    CRITICAL = "critical"  # 严重

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """从字符串创建"""
        mapping = {
            "normal": cls.NORMAL,
            "info": cls.INFO,
            "warning": cls.WARNING,
            "critical": cls.CRITICAL,
        }
        return mapping.get(value.lower(), cls.NORMAL)


class DetectionLevel(Enum):
    """检测级别"""

    FAST = 1  # 快速筛查 (<5ms)
    STANDARD = 2  # 标准检测 (<20ms)
    DEEP = 3  # 深度分析 (<100ms)

    @classmethod
    def from_string(cls, value: str) -> "DetectionLevel":
        """从字符串创建"""
        mapping = {
            "fast": cls.FAST,
            "standard": cls.STANDARD,
            "deep": cls.DEEP,
        }
        return mapping.get(value.lower(), cls.STANDARD)


@dataclass
class DetectionResult:
    """单个检测器的结果"""

    detector_name: str  # 检测器名称
    issue_type: str  # 问题类型 (blur, too_dark, etc.)
    is_abnormal: bool  # 是否异常
    score: float  # 原始得分
    threshold: float  # 使用的阈值
    confidence: float  # 置信度 (0-1)
    severity: Severity  # 严重程度

    # 可解释性字段
    explanation: str = ""  # 解释说明
    possible_causes: List[str] = field(default_factory=list)  # 可能原因
    suggestions: List[str] = field(default_factory=list)  # 建议措施
    evidence: Dict[str, Any] = field(default_factory=dict)  # 证据数据

    # 元数据
    process_time_ms: float = 0  # 处理耗时
    detection_level: DetectionLevel = DetectionLevel.STANDARD

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "detector_name": self.detector_name,
            "issue_type": self.issue_type,
            "is_abnormal": self.is_abnormal,
            "score": round(self.score, 4),
            "threshold": self.threshold,
            "confidence": round(self.confidence, 4),
            "severity": self.severity.value,
            "explanation": self.explanation,
            "possible_causes": self.possible_causes,
            "suggestions": self.suggestions,
            "evidence": {
                k: round(v, 4) if isinstance(v, float) else v
                for k, v in self.evidence.items()
            },
            "process_time_ms": round(self.process_time_ms, 2),
            "detection_level": self.detection_level.name,
        }


class BaseDetector(ABC):
    """检测器基类 - 所有检测器必须继承此类"""

    # 检测器元信息
    name: str = "base_detector"
    display_name: str = "基础检测器"
    description: str = ""
    version: str = "1.0.0"

    # 支持的检测级别
    supported_levels: List[DetectionLevel] = [DetectionLevel.STANDARD]

    # 优先级 (数字越小优先级越高，用于冲突处理)
    priority: int = 100

    # 该检测器会抑制哪些其他检测器的问题类型
    suppresses: List[str] = []

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化检测器

        Args:
            config: 配置字典，包含阈值等配置
        """
        self.config = config or {}
        self._load_thresholds()

    def _load_thresholds(self) -> None:
        """从配置加载阈值 - 子类可重写"""
        pass

    @abstractmethod
    def detect(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
    ) -> DetectionResult:
        """
        执行检测

        Args:
            image: BGR格式的图像数组
            level: 检测级别

        Returns:
            DetectionResult: 检测结果
        """
        pass

    def get_explanation(self, result: DetectionResult) -> str:
        """
        生成解释说明

        Args:
            result: 检测结果

        Returns:
            str: 解释说明文本
        """
        if result.is_abnormal:
            return (
                f"{self.display_name}检测异常: "
                f"得分{result.score:.1f}, 阈值{result.threshold:.1f}"
            )
        return f"{self.display_name}检测正常: 得分{result.score:.1f}"

    def get_possible_causes(self, result: DetectionResult) -> List[str]:
        """
        获取可能原因

        Args:
            result: 检测结果

        Returns:
            List[str]: 可能原因列表
        """
        return []

    def get_suggestions(self, result: DetectionResult) -> List[str]:
        """
        获取建议措施

        Args:
            result: 检测结果

        Returns:
            List[str]: 建议措施列表
        """
        return []

    def _calculate_confidence(
        self,
        score: float,
        threshold: float,
        is_higher_better: bool = True,
    ) -> float:
        """
        计算置信度

        Args:
            score: 检测得分
            threshold: 阈值
            is_higher_better: 分数越高是否越好

        Returns:
            float: 置信度 (0-1)
        """
        if threshold == 0:
            return 1.0

        if is_higher_better:
            # 分数越高越好，低于阈值为异常
            distance_ratio = abs(score - threshold) / threshold
        else:
            # 分数越低越好，高于阈值为异常
            distance_ratio = abs(score - threshold) / max(threshold, 1)

        return min(1.0, distance_ratio)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, priority={self.priority})>"

