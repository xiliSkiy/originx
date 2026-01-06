"""流水线测试"""

import pytest
import numpy as np

# 导入模块
import core.detectors  # noqa
from core import DiagnosisPipeline, DetectionLevel, Severity


class TestDiagnosisPipeline:
    """诊断流水线测试"""

    def test_diagnose_normal_image(self, sample_image, pipeline_config):
        """测试正常图像诊断"""
        pipeline = DiagnosisPipeline(pipeline_config)
        result = pipeline.diagnose(
            sample_image,
            level=DetectionLevel.STANDARD,
            image_id="test_001",
        )

        assert result.image_id == "test_001"
        assert len(result.detection_results) > 0
        assert result.total_process_time_ms > 0
        assert result.timestamp != ""

    def test_diagnose_black_image(self, black_image, pipeline_config):
        """测试黑屏图像诊断"""
        pipeline = DiagnosisPipeline(pipeline_config)
        result = pipeline.diagnose(black_image, level=DetectionLevel.STANDARD)

        assert result.is_abnormal
        # 黑屏应该是主要问题之一
        assert result.primary_issue in ["black_screen", "too_dark", "signal_loss"]

    def test_diagnose_blur_image(self, blur_image, pipeline_config):
        """测试模糊图像诊断"""
        pipeline = DiagnosisPipeline(pipeline_config)
        result = pipeline.diagnose(blur_image, level=DetectionLevel.STANDARD)

        # 检查是否检测到模糊
        blur_results = [
            r for r in result.detection_results if r.detector_name == "blur"
        ]
        assert len(blur_results) > 0

    def test_diagnose_with_specific_detectors(self, sample_image, pipeline_config):
        """测试指定检测器"""
        pipeline = DiagnosisPipeline(pipeline_config)
        result = pipeline.diagnose(
            sample_image,
            level=DetectionLevel.STANDARD,
            detectors=["blur", "brightness"],
        )

        detector_names = [r.detector_name for r in result.detection_results]
        assert "blur" in detector_names
        assert "brightness" in detector_names
        # 不应该有其他检测器
        assert len(detector_names) == 2

    def test_suppression_rules(self, black_image, pipeline_config):
        """测试抑制规则"""
        pipeline = DiagnosisPipeline(pipeline_config)
        result = pipeline.diagnose(black_image, level=DetectionLevel.STANDARD)

        # 如果有黑屏/信号丢失，其他问题应该被抑制
        if "black_screen" in result.independent_issues or "signal_loss" in result.independent_issues:
            # too_dark 应该被抑制
            assert "too_dark" in result.suppressed_issues or "too_dark" not in [
                r.issue_type for r in result.detection_results if r.is_abnormal
            ]

    def test_result_to_dict(self, sample_image, pipeline_config):
        """测试结果序列化"""
        pipeline = DiagnosisPipeline(pipeline_config)
        result = pipeline.diagnose(sample_image, level=DetectionLevel.FAST)

        result_dict = result.to_dict()

        assert "image_id" in result_dict
        assert "is_abnormal" in result_dict
        assert "detection_results" in result_dict
        assert "scores" in result_dict
        assert "total_process_time_ms" in result_dict

    def test_parallel_vs_sequential(self, sample_image):
        """测试并行与顺序执行"""
        config_parallel = {
            "parallel_detection": True,
            "max_workers": 4,
        }
        config_sequential = {
            "parallel_detection": False,
        }

        pipeline_parallel = DiagnosisPipeline(config_parallel)
        pipeline_sequential = DiagnosisPipeline(config_sequential)

        result_parallel = pipeline_parallel.diagnose(
            sample_image, level=DetectionLevel.STANDARD
        )
        result_sequential = pipeline_sequential.diagnose(
            sample_image, level=DetectionLevel.STANDARD
        )

        # 结果应该相同
        assert result_parallel.is_abnormal == result_sequential.is_abnormal
        assert len(result_parallel.detection_results) == len(
            result_sequential.detection_results
        )

    def test_batch_diagnose(self, sample_image, blur_image, pipeline_config):
        """测试批量诊断"""
        pipeline = DiagnosisPipeline(pipeline_config)

        images = [
            {"image": sample_image, "image_id": "img_001"},
            {"image": blur_image, "image_id": "img_002"},
        ]

        results = pipeline.diagnose_batch(images, level=DetectionLevel.FAST)

        assert len(results) == 2
        assert results[0].image_id == "img_001"
        assert results[1].image_id == "img_002"

