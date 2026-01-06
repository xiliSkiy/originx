"""检测流水线"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from .base import BaseDetector, DetectionLevel, DetectionResult, Severity
from .registry import DetectorRegistry


@dataclass
class DiagnosisResult:
    """完整诊断结果"""

    # 基本信息
    image_id: str = ""
    image_path: str = ""
    image_size: tuple = (0, 0)

    # 总体判断
    is_abnormal: bool = False
    primary_issue: Optional[str] = None
    severity: Severity = Severity.NORMAL

    # 详细结果
    detection_results: List[DetectionResult] = field(default_factory=list)
    suppressed_issues: List[str] = field(default_factory=list)
    independent_issues: List[str] = field(default_factory=list)

    # 分数汇总
    scores: Dict[str, float] = field(default_factory=dict)

    # 元数据
    total_process_time_ms: float = 0
    detection_level: DetectionLevel = DetectionLevel.STANDARD
    config_profile: str = "normal"
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（便于JSON序列化）"""
        return {
            "image_id": self.image_id,
            "image_path": self.image_path,
            "image_size": list(self.image_size),
            "is_abnormal": self.is_abnormal,
            "primary_issue": self.primary_issue,
            "severity": self.severity.value,
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
            "detection_results": [r.to_dict() for r in self.detection_results],
            "suppressed_issues": self.suppressed_issues,
            "independent_issues": self.independent_issues,
            "total_process_time_ms": round(self.total_process_time_ms, 2),
            "detection_level": self.detection_level.name,
            "config_profile": self.config_profile,
            "timestamp": self.timestamp,
        }

    def get_abnormal_results(self) -> List[DetectionResult]:
        """获取所有异常检测结果"""
        return [r for r in self.detection_results if r.is_abnormal]

    def get_all_suggestions(self) -> List[str]:
        """获取所有建议措施（去重）"""
        suggestions = []
        for result in self.detection_results:
            if result.is_abnormal:
                for suggestion in result.suggestions:
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
        return suggestions

    def get_all_causes(self) -> List[str]:
        """获取所有可能原因（去重）"""
        causes = []
        for result in self.detection_results:
            if result.is_abnormal:
                for cause in result.possible_causes:
                    if cause not in causes:
                        causes.append(cause)
        return causes


class DiagnosisPipeline:
    """诊断流水线 - 编排检测器执行"""

    # 优先级抑制规则 (高优先级问题会抑制低优先级)
    SUPPRESSION_RULES: Dict[str, List[str]] = {
        "signal_loss": ["too_dark", "blur", "low_contrast", "no_texture", "noise"],
        "black_screen": ["too_dark", "blur", "low_contrast", "no_texture", "noise"],
        "blue_screen": ["color_cast", "low_contrast", "low_saturation"],
        "green_screen": ["color_cast", "low_contrast", "low_saturation"],
        "snow_noise": ["blur", "noise"],
        "occlusion": ["partial_blur", "blur"],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化流水线

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.profile = self.config.get("profile", "normal")
        self.parallel = self.config.get("parallel_detection", True)
        self.max_workers = self.config.get("max_workers", 4)

    def diagnose(
        self,
        image: np.ndarray,
        level: DetectionLevel = DetectionLevel.STANDARD,
        detectors: Optional[List[str]] = None,
        image_id: str = "",
        image_path: str = "",
    ) -> DiagnosisResult:
        """
        执行完整诊断

        Args:
            image: BGR格式图像
            level: 检测级别
            detectors: 指定检测器列表，None表示使用该级别所有检测器
            image_id: 图像ID
            image_path: 图像路径

        Returns:
            DiagnosisResult: 完整诊断结果
        """
        start_time = time.time()

        # 验证图像
        if image is None or image.size == 0:
            return self._create_error_result(
                image_id, image_path, "Invalid image", level
            )

        # 获取检测器
        detector_instances = self._get_detectors(detectors, level)

        if not detector_instances:
            return self._create_error_result(
                image_id, image_path, "No detectors available", level
            )

        # 执行检测
        if self.parallel and len(detector_instances) > 1:
            detection_results = self._parallel_detect(image, detector_instances, level)
        else:
            detection_results = self._sequential_detect(
                image, detector_instances, level
            )

        # 聚合结果
        result = self._aggregate_results(
            detection_results,
            image_id=image_id,
            image_path=image_path,
            image_size=(image.shape[1], image.shape[0]),
            level=level,
        )

        result.total_process_time_ms = (time.time() - start_time) * 1000
        result.timestamp = datetime.now().isoformat()
        result.config_profile = self.profile

        return result

    def diagnose_batch(
        self,
        images: List[Dict[str, Any]],
        level: DetectionLevel = DetectionLevel.STANDARD,
        detectors: Optional[List[str]] = None,
    ) -> List[DiagnosisResult]:
        """
        批量诊断

        Args:
            images: 图像列表，每个元素包含 'image', 'image_id', 'image_path'
            level: 检测级别
            detectors: 指定检测器列表

        Returns:
            List[DiagnosisResult]: 诊断结果列表
        """
        results = []
        for item in images:
            result = self.diagnose(
                image=item.get("image"),
                level=level,
                detectors=detectors,
                image_id=item.get("image_id", ""),
                image_path=item.get("image_path", ""),
            )
            results.append(result)
        return results

    def _get_detectors(
        self,
        detector_names: Optional[List[str]],
        level: DetectionLevel,
    ) -> List[BaseDetector]:
        """获取检测器实例列表"""
        if detector_names:
            return DetectorRegistry.get_by_names(detector_names, self.config)
        return DetectorRegistry.get_by_level(level, self.config)

    def _sequential_detect(
        self,
        image: np.ndarray,
        detectors: List[BaseDetector],
        level: DetectionLevel,
    ) -> List[DetectionResult]:
        """顺序执行检测"""
        results = []
        for detector in detectors:
            try:
                result = detector.detect(image, level)
                results.append(result)
            except Exception as e:
                # 记录错误但继续执行其他检测器
                print(f"Detector {detector.name} failed: {e}")
        return results

    def _parallel_detect(
        self,
        image: np.ndarray,
        detectors: List[BaseDetector],
        level: DetectionLevel,
    ) -> List[DetectionResult]:
        """并行执行检测"""
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_detector = {
                executor.submit(detector.detect, image, level): detector
                for detector in detectors
            }

            # 收集结果
            for future in as_completed(future_to_detector):
                detector = future_to_detector[future]
                try:
                    result = future.result(timeout=5)
                    results.append(result)
                except Exception as e:
                    print(f"Detector {detector.name} failed: {e}")

        return results

    def _aggregate_results(
        self,
        detection_results: List[DetectionResult],
        image_id: str,
        image_path: str,
        image_size: tuple,
        level: DetectionLevel,
    ) -> DiagnosisResult:
        """聚合检测结果，处理优先级和冲突"""

        # 按优先级排序（优先级数字小的在前）
        sorted_results = sorted(
            detection_results,
            key=lambda r: self._get_detector_priority(r.detector_name),
        )

        # 找出异常结果
        abnormal_results = [r for r in sorted_results if r.is_abnormal]

        # 应用抑制规则
        suppressed_issues = []
        active_issues = []

        for result in abnormal_results:
            issue = result.issue_type

            # 检查是否被更高优先级问题抑制
            is_suppressed = False
            for high_priority_issue in active_issues:
                suppressible = self.SUPPRESSION_RULES.get(high_priority_issue, [])
                if issue in suppressible:
                    suppressed_issues.append(issue)
                    is_suppressed = True
                    break

            if not is_suppressed:
                active_issues.append(issue)

        # 确定主要问题和严重程度
        primary_issue = active_issues[0] if active_issues else None
        severity = Severity.NORMAL

        if active_issues:
            # 找到主要问题对应的结果，确定严重程度
            for result in abnormal_results:
                if result.issue_type == primary_issue:
                    severity = result.severity
                    break

        # 汇总分数
        scores = {r.detector_name: r.score for r in sorted_results}

        return DiagnosisResult(
            image_id=image_id,
            image_path=image_path,
            image_size=image_size,
            is_abnormal=len(active_issues) > 0,
            primary_issue=primary_issue,
            severity=severity,
            detection_results=sorted_results,
            suppressed_issues=suppressed_issues,
            independent_issues=active_issues,
            scores=scores,
            detection_level=level,
        )

    def _get_detector_priority(self, detector_name: str) -> int:
        """获取检测器优先级"""
        info = DetectorRegistry.get_detector_info(detector_name)
        return info.get("priority", 100) if info else 100

    def _create_error_result(
        self,
        image_id: str,
        image_path: str,
        error_message: str,
        level: DetectionLevel,
    ) -> DiagnosisResult:
        """创建错误结果"""
        return DiagnosisResult(
            image_id=image_id,
            image_path=image_path,
            image_size=(0, 0),
            is_abnormal=True,
            primary_issue="error",
            severity=Severity.CRITICAL,
            detection_results=[],
            suppressed_issues=[],
            independent_issues=["error"],
            scores={},
            total_process_time_ms=0,
            detection_level=level,
            config_profile=self.profile,
            timestamp=datetime.now().isoformat(),
        )

    def add_suppression_rule(self, issue: str, suppresses: List[str]) -> None:
        """
        添加抑制规则

        Args:
            issue: 高优先级问题类型
            suppresses: 被抑制的问题类型列表
        """
        self.SUPPRESSION_RULES[issue] = suppresses

    def remove_suppression_rule(self, issue: str) -> bool:
        """
        移除抑制规则

        Args:
            issue: 问题类型

        Returns:
            bool: 是否成功移除
        """
        if issue in self.SUPPRESSION_RULES:
            del self.SUPPRESSION_RULES[issue]
            return True
        return False

