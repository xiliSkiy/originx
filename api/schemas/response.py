"""响应模型定义"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """基础响应"""

    code: int = Field(0, description="状态码，0表示成功")
    message: str = Field("success", description="状态消息")


class MetaInfo(BaseModel):
    """元信息"""

    process_time_ms: float = Field(..., description="处理耗时(毫秒)")
    detection_level: str = Field(..., description="检测级别")
    profile: str = Field(..., description="配置模板")
    version: str = Field("1.0.0", description="API版本")
    timestamp: str = Field(..., description="时间戳")


class IssueDetail(BaseModel):
    """问题详情"""

    type: str = Field(..., description="问题类型")
    is_abnormal: bool = Field(..., description="是否异常")
    score: float = Field(..., description="得分")
    threshold: float = Field(..., description="阈值")
    confidence: float = Field(..., description="置信度")
    severity: str = Field(..., description="严重程度")
    explanation: str = Field(..., description="解释说明")
    possible_causes: List[str] = Field(default_factory=list, description="可能原因")
    suggestions: List[str] = Field(default_factory=list, description="建议措施")
    evidence: Optional[Dict[str, Any]] = Field(None, description="证据数据")


class DiagnoseData(BaseModel):
    """诊断数据"""

    task_id: str = Field(..., description="任务ID")
    is_abnormal: bool = Field(..., description="是否异常")
    primary_issue: Optional[str] = Field(None, description="主要问题")
    severity: str = Field(..., description="严重程度")
    scores: Dict[str, float] = Field(..., description="各检测器得分")
    issues: List[IssueDetail] = Field(..., description="问题详情列表")
    suppressed_issues: List[str] = Field(default_factory=list, description="被抑制的问题")
    image_info: Optional[Dict[str, Any]] = Field(None, description="图像信息")


class DiagnoseResponse(BaseResponse):
    """单图诊断响应"""

    data: Optional[DiagnoseData] = None
    meta: Optional[MetaInfo] = None


class BatchSummary(BaseModel):
    """批量诊断汇总"""

    total_images: int = Field(..., description="总图像数")
    abnormal_count: int = Field(..., description="异常数量")
    normal_count: int = Field(..., description="正常数量")
    issue_distribution: Dict[str, int] = Field(..., description="问题分布")


class BatchDiagnoseData(BaseModel):
    """批量诊断数据"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: Dict[str, int] = Field(..., description="进度信息")
    results: Optional[List[DiagnoseData]] = Field(None, description="诊断结果列表")
    summary: Optional[BatchSummary] = Field(None, description="汇总信息")


class BatchDiagnoseResponse(BaseResponse):
    """批量诊断响应"""

    data: Optional[BatchDiagnoseData] = None
    meta: Optional[MetaInfo] = None


class ThresholdsInfo(BaseModel):
    """阈值信息"""

    blur_threshold: float
    brightness_min: float
    brightness_max: float
    contrast_min: float
    saturation_min: float
    color_cast_threshold: float
    noise_threshold: float
    stripe_threshold: float


class ProfileInfo(BaseModel):
    """配置模板信息"""

    name: str
    display_name: str
    description: str
    thresholds: ThresholdsInfo


class ConfigData(BaseModel):
    """配置数据"""

    profile: str
    detection_level: str
    parallel_detection: bool
    max_workers: int
    gpu_enabled: bool
    thresholds: ThresholdsInfo


class ConfigResponse(BaseResponse):
    """配置响应"""

    data: Optional[ConfigData] = None


class ProfileListResponse(BaseResponse):
    """配置模板列表响应"""

    data: Optional[List[ProfileInfo]] = None


class DetectorInfo(BaseModel):
    """检测器信息"""

    name: str = Field(..., description="检测器名称")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="描述")
    version: str = Field(..., description="版本")
    priority: int = Field(..., description="优先级")
    supported_levels: List[str] = Field(..., description="支持的检测级别")
    suppresses: List[str] = Field(default_factory=list, description="抑制的问题类型")


class DetectorListResponse(BaseResponse):
    """检测器列表响应"""

    data: Optional[List[DetectorInfo]] = None


class DetectorInfoResponse(BaseResponse):
    """检测器详情响应"""

    data: Optional[DetectorInfo] = None


class HealthData(BaseModel):
    """健康检查数据"""

    status: str = Field(..., description="状态")
    uptime_seconds: float = Field(..., description="运行时间(秒)")
    detectors_loaded: int = Field(..., description="已加载检测器数量")


class HealthResponse(BaseResponse):
    """健康检查响应"""

    data: Optional[HealthData] = None


class SystemInfoData(BaseModel):
    """系统信息数据"""

    version: str = Field(..., description="版本")
    python_version: str = Field(..., description="Python版本")
    opencv_version: str = Field(..., description="OpenCV版本")
    detectors_count: int = Field(..., description="检测器数量")
    supported_formats: List[str] = Field(..., description="支持的图像格式")
    gpu_available: bool = Field(..., description="GPU是否可用")


class SystemInfoResponse(BaseResponse):
    """系统信息响应"""

    data: Optional[SystemInfoData] = None

