
"""噪声检测器"""

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from ..base import BaseDetector, DetectionLevel, DetectionResult, Severity
from ..registry import DetectorRegistry


@DetectorRegistry.register
class NoiseDetector(BaseDetector):
    """
    噪声检测器

  检测图像噪声水平，包括：
  - 高斯噪声
  - 椒盐噪声
  - 雪花噪声
  """

  name = "noise"
  display_name = "图像噪声检测"
  description = "检测图像噪声水平，包括高斯噪声、椒盐噪声、雪花噪声"
  version = "1.0.0"

  supported_levels = [
      DetectionLevel.FAST,
      DetectionLevel.STANDARD,
      DetectionLevel.DEEP,
  ]

  priority = 55  # 中等优先级
  suppresses = []

  # 默认阈值
  DEFAULT_THRESHOLD = 15.0

  def __init__(self, config: Dict[str, Any] = None):
      super().__init__(config)

  def _load_thresholds(self) -> None:
      """从配置加载阈值"""
      self.noise_threshold = self.config.get("noise_threshold", self.DEFAULT_THRESHOLD)

  def detect(
      self,
      image: np.ndarray,
      level: DetectionLevel = DetectionLevel.STANDARD,
  ) -> DetectionResult:
      """执行噪声检测"""
      start_time = time.time()

      gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

      # 根据检测级别选择算法
      if level == DetectionLevel.FAST:
          noise_level, evidence = self._fast_detect(gray)
      elif level == DetectionLevel.STANDARD:
          noise_level, evidence = self._standard_detect(gray)
      else:
          noise_level, evidence = self._deep_detect(gray, image)

      # 判断异常（噪声越高越异常）
      is_abnormal = noise_level > self.noise_threshold

      # 计算置信度
      if is_abnormal:
          confidence = min(1.0, (noise_level - self.noise_threshold) / self.noise_threshold)
      else:
          confidence = min(1.0, (self.noise_threshold - noise_level) / self.noise_threshold)

      # 确定严重程度
      severity = self._calculate_severity(noise_level)

      # 确定噪声类型
      issue_type = self._determine_noise_type(evidence) if is_abnormal else "noise_normal"

      evidence["noise_threshold"] = self.noise_threshold

      process_time = (time.time() - start_time) * 1000

      result = DetectionResult(
          detector_name=self.name,
          issue_type=issue_type,
          is_abnormal=is_abnormal,
          score=noise_level,
          threshold=self.noise_threshold,
          confidence=confidence,
          severity=severity,
          evidence=evidence,
          process_time_ms=process_time,
          detection_level=level,
      )

      result.explanation = self.get_explanation(result)
      result.possible_causes = self.get_possible_causes(result)
      result.suggestions = self.get_suggestions(result)

      return result

  def _fast_detect(self, gray: np.ndarray) -> tuple:
      """快速检测 - 使用拉普拉斯算子估计，考虑纹理影响"""
      laplacian = cv2.Laplacian(gray, cv2.CV_64F)
      raw_sigma = np.median(np.abs(laplacian)) / 0.6745

      # 计算图像纹理复杂度，用于修正噪声估计
      # 使用局部方差来评估纹理丰富程度
      kernel_size = 5
      kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
      local_mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
      local_variance = cv2.filter2D((gray.astype(np.float32) - local_mean) ** 2, -1, kernel)
      texture_complexity = np.median(local_variance)

      # 如果纹理复杂度高，可能是图像细节而非噪声
      # 使用自适应阈值：纹理越复杂，对噪声的容忍度越高
      texture_factor = min(1.0, 50.0 / max(texture_complexity, 1.0))
      adjusted_sigma = raw_sigma * texture_factor

      # 进一步修正：如果图像整体对比度较高，可能是正常纹理
      image_contrast = np.std(gray)
      if image_contrast > 40:  # 对比度较高的图像
          contrast_factor = min(1.0, 40.0 / max(image_contrast, 1.0))
          adjusted_sigma = adjusted_sigma * (0.7 + 0.3 * contrast_factor)

      return float(adjusted_sigma), {
          "estimation_method": "laplacian_mad_adaptive",
          "noise_sigma": float(raw_sigma),
          "adjusted_sigma": float(adjusted_sigma),
          "texture_complexity": float(texture_complexity),
          "image_contrast": float(image_contrast),
      }

  def _standard_detect(self, gray: np.ndarray) -> tuple:
      """标准检测 - 使用中值滤波残差，考虑纹理影响"""
      # 中值滤波
      filtered = cv2.medianBlur(gray, 5)
      residual = gray.astype(float) - filtered.astype(float)
      noise_std = float(np.std(residual))

      # 拉普拉斯估计
      laplacian = cv2.Laplacian(gray, cv2.CV_64F)
      raw_noise_mad = float(np.median(np.abs(laplacian)) / 0.6745)

      # 计算纹理复杂度
      kernel_size = 5
      kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
      local_mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
      local_variance = cv2.filter2D((gray.astype(np.float32) - local_mean) ** 2, -1, kernel)
      texture_complexity = np.median(local_variance)

      # 自适应修正拉普拉斯估计
      texture_factor = min(1.0, 50.0 / max(texture_complexity, 1.0))
      noise_mad = raw_noise_mad * texture_factor

      # 图像对比度修正
      image_contrast = np.std(gray)
      if image_contrast > 40:
          contrast_factor = min(1.0, 40.0 / max(image_contrast, 1.0))
          noise_mad = noise_mad * (0.7 + 0.3 * contrast_factor)

      # 综合估计（更倾向于使用残差方法，因为它对纹理不敏感）
      noise_level = (noise_std * 0.6 + noise_mad * 0.4)

      return noise_level, {
          "estimation_method": "combined_adaptive",
          "noise_std_residual": noise_std,
          "noise_mad_laplacian": float(raw_noise_mad),
          "adjusted_mad": noise_mad,
          "texture_complexity": float(texture_complexity),
          "image_contrast": float(image_contrast),
          "combined_estimate": noise_level,
      }

  def _deep_detect(self, gray: np.ndarray, color_image: np.ndarray) -> tuple:
      """深度检测 - 多方法综合分析"""
      evidence = {"estimation_method": "deep"}

      # 方法1：中值滤波残差
      filtered = cv2.medianBlur(gray, 5)
      residual = gray.astype(float) - filtered.astype(float)
      noise_std = float(np.std(residual))
      evidence["noise_std_residual"] = noise_std

      # 方法2：拉普拉斯MAD估计
      laplacian = cv2.Laplacian(gray, cv2.CV_64F)
      noise_mad = float(np.median(np.abs(laplacian)) / 0.6745)
      evidence["noise_mad_laplacian"] = noise_mad

      # 方法3：高频能量分析
      f = np.fft.fft2(gray)
      fshift = np.fft.fftshift(f)
      magnitude = np.abs(fshift)

      h, w = magnitude.shape
      cy, cx = h // 2, w // 2

      # 高频区域能量
      high_freq_mask = np.ones_like(magnitude, dtype=bool)
      high_freq_mask[cy - h // 8 : cy + h // 8, cx - w // 8 : cx + w // 8] = False
      high_freq_energy = float(magnitude[high_freq_mask].mean())
      total_energy = float(magnitude.mean())
      high_freq_ratio = high_freq_energy / total_energy if total_energy > 0 else 0

      evidence["high_freq_ratio"] = high_freq_ratio

      # 方法4：椒盐噪声检测
      salt_pepper_ratio = self._detect_salt_pepper(gray)
      evidence["salt_pepper_ratio"] = salt_pepper_ratio

      # 方法5：雪花噪声检测（彩色）
      snow_ratio = self._detect_snow_noise(color_image)
      evidence["snow_noise_ratio"] = snow_ratio

      # 综合噪声水平
      noise_level = (noise_std + noise_mad) / 2

      # 如果检测到椒盐或雪花，提高噪声评分
      if salt_pepper_ratio > 0.01:
          noise_level = max(noise_level, salt_pepper_ratio * 1000)
      if snow_ratio > 0.01:
          noise_level = max(noise_level, snow_ratio * 1000)

      evidence["combined_estimate"] = noise_level

      return noise_level, evidence

  def _detect_salt_pepper(self, gray: np.ndarray) -> float:
      """检测椒盐噪声"""
      # 统计极值像素占比
      salt = np.sum(gray > 250)
      pepper = np.sum(gray < 5)
      total = gray.size

      ratio = (salt + pepper) / total
      return float(ratio)

  def _detect_snow_noise(self, image: np.ndarray) -> float:
      """检测雪花噪声"""
      # 雪花噪声通常表现为亮点
      hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
      v_channel = hsv[:, :, 2]
      s_channel = hsv[:, :, 1]

      # 高亮度、低饱和度的点
      snow_mask = (v_channel > 240) & (s_channel < 30)
      snow_ratio = float(np.sum(snow_mask)) / snow_mask.size

      return snow_ratio

  def _determine_noise_type(self, evidence: dict) -> str:
      """确定噪声类型"""
      salt_pepper = evidence.get("salt_pepper_ratio", 0)
      snow = evidence.get("snow_noise_ratio", 0)

      if snow > 0.02:
          return "snow_noise"
      elif salt_pepper > 0.01:
          return "salt_pepper_noise"
      else:
          return "gaussian_noise"

  def _calculate_severity(self, noise_level: float) -> Severity:
      """计算严重程度"""
      if noise_level <= self.noise_threshold:
          return Severity.NORMAL
      elif noise_level <= self.noise_threshold * 1.5:
          return Severity.INFO
      elif noise_level <= self.noise_threshold * 2.5:
          return Severity.WARNING
      else:
          return Severity.CRITICAL

  def get_explanation(self, result: DetectionResult) -> str:
      """生成解释说明"""
      noise_level = result.score
      issue_type = result.issue_type

      if not result.is_abnormal:
          return f"噪声水平{noise_level:.1f}，在正常范围内"

      type_names = {
          "gaussian_noise": "高斯噪声",
          "salt_pepper_noise": "椒盐噪声",
          "snow_noise": "雪花噪声",
      }
      type_name = type_names.get(issue_type, "噪声")

      return (
          f"检测到{type_name}，噪声水平{noise_level:.1f}，"
          f"超过阈值{self.noise_threshold:.1f}"
      )

  def get_possible_causes(self, result: DetectionResult) -> List[str]:
      """获取可能原因"""
      if not result.is_abnormal:
          return []

      issue_type = result.issue_type
      causes = ["环境光线不足", "摄像头增益设置过高"]

      if issue_type == "salt_pepper_noise":
          causes.extend([
              "传感器老化或损坏",
              "模数转换器故障",
              "信号传输干扰",
          ])
      elif issue_type == "snow_noise":
          causes.extend([
              "信号弱或无信号",
              "模拟信号干扰",
              "连接不良",
          ])
      else:  # gaussian_noise
          causes.extend([
              "高ISO/增益设置",
              "传感器热噪声",
              "光线严重不足",
          ])

      return causes

  def get_suggestions(self, result: DetectionResult) -> List[str]:
      """获取建议措施"""
      if not result.is_abnormal:
          return []

      issue_type = result.issue_type
      suggestions = [
          "改善环境照明",
          "降低摄像头增益设置",
      ]

      if issue_type == "salt_pepper_noise":
          suggestions.extend([
              "检查摄像头传感器状态",
              "检查信号线连接",
          ])
      elif issue_type == "snow_noise":
          suggestions.extend([
              "检查信号线连接",
              "检查视频源设备",
              "更换信号线",
          ])
      else:
          suggestions.extend([
              "启用降噪功能",
              "考虑更换低噪声摄像头",
          ])

      return suggestions

