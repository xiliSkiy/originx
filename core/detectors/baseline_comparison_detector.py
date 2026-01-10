# -*- coding: utf-8 -*-
"""
基准图像对比检测器

与标准参考图像进行对比，检测是否存在显著差异
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, List
from skimage.metrics import structural_similarity as ssim

from core.base import BaseDetector, DetectionResult, Severity


class BaselineComparisonDetector(BaseDetector):
    """基准图像对比检测器"""
    
    name = "baseline_comparison"
    display_name = "基准图像对比"
    description = "与标准参考图像进行对比检测"
    
    default_config = {
        "ssim_threshold": 0.85,          # SSIM 相似度阈值
        "histogram_threshold": 0.80,      # 直方图相似度阈值
        "feature_match_threshold": 0.7,   # 特征点匹配阈值
        "diff_threshold": 0.15,           # 差异阈值（15%）
        "enable_region_analysis": True,   # 是否启用区域差异分析
        "region_grid_size": 3,           # 区域网格大小（3x3）
    }
    
    def __init__(self, baseline_image: np.ndarray, config: Optional[Dict] = None):
        """
        初始化对比检测器
        
        Args:
            baseline_image: 基准参考图像（BGR格式）
            config: 配置参数
        """
        # 合并默认配置
        merged_config = {**self.default_config}
        if config:
            merged_config.update(config)
        super().__init__(merged_config)
        
        if baseline_image is None or baseline_image.size == 0:
            raise ValueError("Baseline image cannot be None or empty")
        
        self.baseline_image = baseline_image.copy()
        
        # 预处理基准图像
        self.baseline_gray = cv2.cvtColor(baseline_image, cv2.COLOR_BGR2GRAY)
        self.baseline_hist = self._calculate_histogram(baseline_image)
        self.baseline_features = self._extract_features(self.baseline_gray)
    
    def detect(self, image: np.ndarray) -> DetectionResult:
        """
        对比目标图像与基准图像
        
        Args:
            image: 待检测图像（BGR格式）
            
        Returns:
            DetectionResult: 检测结果
        """
        import time
        start_time = time.time()
        
        # 确保图像尺寸一致
        if image.shape != self.baseline_image.shape:
            image = cv2.resize(
                image,
                (self.baseline_image.shape[1], self.baseline_image.shape[0])
            )
        
        target_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        target_hist = self._calculate_histogram(image)
        target_features = self._extract_features(target_gray)
        
        # 1. SSIM 结构相似度
        ssim_score = self._calculate_ssim(self.baseline_gray, target_gray)
        
        # 2. 直方图相似度
        hist_similarity = self._compare_histograms(self.baseline_hist, target_hist)
        
        # 3. 特征点匹配
        feature_match_score = self._match_features(
            self.baseline_features,
            target_features
        )
        
        # 4. 区域差异分析
        region_diffs = []
        if self.config["enable_region_analysis"]:
            region_diffs = self._analyze_region_differences(
                self.baseline_gray,
                target_gray
            )
        
        # 5. 综合判断
        is_abnormal = self._judge_abnormal(
            ssim_score,
            hist_similarity,
            feature_match_score,
            region_diffs
        )
        
        # 6. 计算综合相似度
        overall_similarity = (ssim_score + hist_similarity + feature_match_score) / 3
        
        # 7. 差异可视化
        diff_image = self._visualize_difference(
            self.baseline_image,
            image
        )
        
        process_time_ms = (time.time() - start_time) * 1000
        
        # 生成解释和建议
        explanation = self._generate_explanation(
            is_abnormal,
            ssim_score,
            hist_similarity,
            feature_match_score
        )
        suggestions = self._generate_suggestions(is_abnormal)
        
        return DetectionResult(
            detector_name=self.name,
            is_abnormal=is_abnormal,
            score=1.0 - overall_similarity,  # 差异分数
            threshold=1.0 - self.config["ssim_threshold"],
            confidence=overall_similarity,
            issue_type="baseline_mismatch" if is_abnormal else "normal",
            severity=self._calculate_severity(1.0 - overall_similarity, 1.0 - self.config["ssim_threshold"]),
            explanation=explanation,
            suggestions=suggestions,
            evidence={
                "ssim_score": float(ssim_score),
                "histogram_similarity": float(hist_similarity),
                "feature_match_score": float(feature_match_score),
                "overall_similarity": float(overall_similarity),
                "region_differences": region_diffs,
                "diff_image_shape": list(diff_image.shape) if diff_image is not None else None,
            },
            process_time_ms=process_time_ms,
        )
    
    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """计算 SSIM"""
        try:
            score = ssim(img1, img2, data_range=255)
            return float(score)
        except:
            return 0.0
    
    def _calculate_histogram(self, image: np.ndarray) -> np.ndarray:
        """计算颜色直方图"""
        hist_b = cv2.calcHist([image], [0], None, [256], [0, 256])
        hist_g = cv2.calcHist([image], [1], None, [256], [0, 256])
        hist_r = cv2.calcHist([image], [2], None, [256], [0, 256])
        hist = np.concatenate([hist_b, hist_g, hist_r])
        return hist
    
    def _compare_histograms(self, hist1: np.ndarray, hist2: np.ndarray) -> float:
        """比较直方图相似度"""
        similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return float(similarity)
    
    def _extract_features(self, image: np.ndarray) -> tuple:
        """提取特征点"""
        # 使用 ORB 特征检测器
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, descriptors = orb.detectAndCompute(image, None)
        return (keypoints, descriptors)
    
    def _match_features(
        self,
        features1: tuple,
        features2: tuple
    ) -> float:
        """匹配特征点"""
        kp1, desc1 = features1
        kp2, desc2 = features2
        
        if desc1 is None or desc2 is None or len(desc1) == 0 or len(desc2) == 0:
            return 0.0
        
        # 使用 BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(desc1, desc2)
        
        if len(matches) == 0:
            return 0.0
        
        # 计算匹配分数
        match_score = len(matches) / max(len(kp1), len(kp2))
        return float(match_score)
    
    def _analyze_region_differences(
        self,
        img1: np.ndarray,
        img2: np.ndarray
    ) -> List[Dict[str, Any]]:
        """区域差异分析"""
        h, w = img1.shape
        grid_size = self.config["region_grid_size"]
        cell_h = h // grid_size
        cell_w = w // grid_size
        
        region_diffs = []
        
        for i in range(grid_size):
            for j in range(grid_size):
                y1 = i * cell_h
                y2 = (i + 1) * cell_h if i < grid_size - 1 else h
                x1 = j * cell_w
                x2 = (j + 1) * cell_w if j < grid_size - 1 else w
                
                region1 = img1[y1:y2, x1:x2]
                region2 = img2[y1:y2, x1:x2]
                
                # 计算区域 SSIM
                try:
                    region_ssim = ssim(region1, region2, data_range=255)
                except:
                    region_ssim = 0.0
                
                region_diffs.append({
                    "region": [int(i), int(j)],
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "ssim": float(region_ssim),
                    "is_abnormal": bool(region_ssim < self.config["ssim_threshold"])
                })
        
        return region_diffs
    
    def _judge_abnormal(
        self,
        ssim_score: float,
        hist_similarity: float,
        feature_match_score: float,
        region_diffs: List[Dict[str, Any]]
    ) -> bool:
        """判断是否异常"""
        # 主要指标判断
        if ssim_score < self.config["ssim_threshold"]:
            return True
        if hist_similarity < self.config["histogram_threshold"]:
            return True
        if feature_match_score < self.config["feature_match_threshold"]:
            return True
        
        # 区域差异判断
        if region_diffs:
            abnormal_regions = [
                r for r in region_diffs
                if r["is_abnormal"]
            ]
            abnormal_ratio = len(abnormal_regions) / len(region_diffs)
            if abnormal_ratio > self.config["diff_threshold"]:
                return True
        
        return False
    
    def _visualize_difference(
        self,
        img1: np.ndarray,
        img2: np.ndarray
    ) -> Optional[np.ndarray]:
        """可视化差异"""
        try:
            # 计算差异图
            diff = cv2.absdiff(img1, img2)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            
            # 阈值化
            _, thresh = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)
            
            # 叠加到原图
            result = img2.copy()
            result[thresh > 0] = [0, 0, 255]  # 差异区域标红
            
            return result
        except:
            return None
    
    def _generate_explanation(
        self,
        is_abnormal: bool,
        ssim_score: float,
        hist_similarity: float,
        feature_match_score: float
    ) -> str:
        """生成解释说明"""
        if is_abnormal:
            reasons = []
            if ssim_score < self.config["ssim_threshold"]:
                reasons.append(f"结构相似度较低 ({ssim_score:.2f})")
            if hist_similarity < self.config["histogram_threshold"]:
                reasons.append(f"颜色分布差异较大 ({hist_similarity:.2f})")
            if feature_match_score < self.config["feature_match_threshold"]:
                reasons.append(f"特征匹配度较低 ({feature_match_score:.2f})")
            
            return f"检测到与基准图像存在显著差异：{', '.join(reasons)}"
        else:
            return f"与基准图像相似度较高 (SSIM: {ssim_score:.2f}, 直方图: {hist_similarity:.2f}, 特征: {feature_match_score:.2f})"
    
    def _generate_suggestions(self, is_abnormal: bool) -> List[str]:
        """生成改进建议"""
        if is_abnormal:
            return [
                "检查摄像头位置是否发生变化",
                "检查画面内容是否正常",
                "检查光照条件是否一致",
                "如为正常变化，请更新基准图像"
            ]
        else:
            return ["画面与基准图像一致，状态正常"]
    
    def _calculate_severity(self, diff_score: float, threshold: float) -> Severity:
        """
        计算严重程度
        
        Args:
            diff_score: 差异分数（0-1，越大差异越大）
            threshold: 差异阈值
            
        Returns:
            Severity: 严重程度
        """
        if diff_score <= threshold:
            return Severity.NORMAL
        
        # 计算差异比例
        ratio = diff_score / threshold if threshold > 0 else float('inf')
        
        if ratio < 1.5:
            return Severity.INFO
        elif ratio < 2.0:
            return Severity.WARNING
        else:
            return Severity.CRITICAL
