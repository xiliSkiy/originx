"""配置管理模块"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import os
import yaml


@dataclass
class DetectionThresholds:
    """检测阈值配置"""

    # 模糊检测 - 分数越高越清晰，低于阈值判定为模糊
    blur_threshold: float = 100.0

    # 亮度检测 - 像素均值范围
    brightness_min: float = 20.0
    brightness_max: float = 235.0

    # 对比度检测 - 标准差，低于阈值判定为低对比度
    contrast_min: float = 30.0

    # 颜色检测
    saturation_min: float = 10.0  # 低于此值判定为黑白/灰度
    color_cast_threshold: float = 30.0  # RGB通道偏差阈值

    # 噪声检测 - 噪声估计值，高于阈值判定为噪声严重
    noise_threshold: float = 15.0

    # 条纹检测 - 频域能量比，高于阈值判定为有条纹
    stripe_threshold: float = 0.3

    # 信号丢失检测
    black_screen_threshold: float = 10.0  # 亮度低于此值判定为黑屏
    
    # 遮挡检测
    occlusion_threshold: float = 0.3  # 遮挡面积比例


@dataclass
class ProfileConfig:
    """配置模板"""

    name: str
    display_name: str
    description: str
    thresholds: DetectionThresholds


# 预设配置模板
PRESET_PROFILES: Dict[str, ProfileConfig] = {
    "strict": ProfileConfig(
        name="strict",
        display_name="严格模式",
        description="适用于金融、银行等对画质要求高的场景",
        thresholds=DetectionThresholds(
            blur_threshold=50.0,
            brightness_min=30.0,
            brightness_max=220.0,
            contrast_min=40.0,
            saturation_min=15.0,
            color_cast_threshold=20.0,
            noise_threshold=10.0,
            stripe_threshold=0.2,
            black_screen_threshold=15.0,
            occlusion_threshold=0.2,
        ),
    ),
    "normal": ProfileConfig(
        name="normal",
        display_name="标准模式",
        description="适用于园区、企业等一般监控场景",
        thresholds=DetectionThresholds(
            noise_threshold=30.0,  # 提高阈值，减少对纹理丰富图像的误报
        ),
    ),
    "loose": ProfileConfig(
        name="loose",
        display_name="宽松模式",
        description="适用于户外、复杂环境等场景",
        thresholds=DetectionThresholds(
            blur_threshold=150.0,
            brightness_min=10.0,
            brightness_max=245.0,
            contrast_min=20.0,
            saturation_min=5.0,
            color_cast_threshold=40.0,
            noise_threshold=25.0,
            stripe_threshold=0.4,
            black_screen_threshold=5.0,
            occlusion_threshold=0.4,
        ),
    ),
}


@dataclass
class ServerConfig:
    """服务器配置"""

    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 4
    timeout: int = 30
    max_request_size: int = 50 * 1024 * 1024  # 50MB


@dataclass
class StorageConfig:
    """存储配置"""

    result_dir: str = "./results"
    sample_dir: str = "./samples"
    keep_days: int = 30
    save_thumbnails: bool = True
    thumbnail_size: tuple = (320, 240)


@dataclass
class LogConfig:
    """日志配置"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class SampleCollectionConfig:
    """样本收集配置"""

    enabled: bool = True
    collect_abnormal: bool = True
    collect_boundary: bool = True  # 收集置信度边界样本
    boundary_range: tuple = (0.3, 0.7)  # 置信度在此区间的为边界样本
    max_samples_per_type: int = 1000


@dataclass
class AppConfig:
    """应用总配置"""

    # 检测配置
    profile: str = "normal"
    detection_level: str = "standard"
    parallel_detection: bool = True
    max_workers: int = 4
    gpu_enabled: bool = False

    # 自定义阈值（覆盖profile中的阈值）
    custom_thresholds: Optional[Dict[str, float]] = None

    # 子配置
    server: ServerConfig = field(default_factory=ServerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    log: LogConfig = field(default_factory=LogConfig)
    sample_collection: SampleCollectionConfig = field(
        default_factory=SampleCollectionConfig
    )

    def get_thresholds(self) -> DetectionThresholds:
        """获取最终阈值配置"""
        # 先获取profile的阈值
        profile = PRESET_PROFILES.get(self.profile, PRESET_PROFILES["normal"])
        # 创建阈值副本
        thresholds = DetectionThresholds(
            blur_threshold=profile.thresholds.blur_threshold,
            brightness_min=profile.thresholds.brightness_min,
            brightness_max=profile.thresholds.brightness_max,
            contrast_min=profile.thresholds.contrast_min,
            saturation_min=profile.thresholds.saturation_min,
            color_cast_threshold=profile.thresholds.color_cast_threshold,
            noise_threshold=profile.thresholds.noise_threshold,
            stripe_threshold=profile.thresholds.stripe_threshold,
            black_screen_threshold=profile.thresholds.black_screen_threshold,
            occlusion_threshold=profile.thresholds.occlusion_threshold,
        )

        # 应用自定义阈值覆盖
        if self.custom_thresholds:
            for key, value in self.custom_thresholds.items():
                if hasattr(thresholds, key):
                    setattr(thresholds, key, value)

        return thresholds

    def get_threshold_dict(self) -> Dict[str, float]:
        """获取阈值字典（便于传递给检测器）"""
        thresholds = self.get_thresholds()
        return {
            "blur_threshold": thresholds.blur_threshold,
            "brightness_min": thresholds.brightness_min,
            "brightness_max": thresholds.brightness_max,
            "contrast_min": thresholds.contrast_min,
            "saturation_min": thresholds.saturation_min,
            "color_cast_threshold": thresholds.color_cast_threshold,
            "noise_threshold": thresholds.noise_threshold,
            "stripe_threshold": thresholds.stripe_threshold,
            "black_screen_threshold": thresholds.black_screen_threshold,
            "occlusion_threshold": thresholds.occlusion_threshold,
        }

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        """从文件加载配置"""
        # 尝试从环境变量获取配置路径
        if config_path is None:
            config_path = os.environ.get("ORIGINX_CONFIG")

        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                return cls._from_dict(data)
        return cls()

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """从字典创建配置"""
        config = cls()

        for key, value in data.items():
            if key == "server" and isinstance(value, dict):
                config.server = ServerConfig(**value)
            elif key == "storage" and isinstance(value, dict):
                # 处理 thumbnail_size 为 tuple
                if "thumbnail_size" in value and isinstance(
                    value["thumbnail_size"], list
                ):
                    value["thumbnail_size"] = tuple(value["thumbnail_size"])
                config.storage = StorageConfig(**value)
            elif key == "log" and isinstance(value, dict):
                config.log = LogConfig(**value)
            elif key == "sample_collection" and isinstance(value, dict):
                # 处理 boundary_range 为 tuple
                if "boundary_range" in value and isinstance(
                    value["boundary_range"], list
                ):
                    value["boundary_range"] = tuple(value["boundary_range"])
                config.sample_collection = SampleCollectionConfig(**value)
            elif hasattr(config, key):
                setattr(config, key, value)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "profile": self.profile,
            "detection_level": self.detection_level,
            "parallel_detection": self.parallel_detection,
            "max_workers": self.max_workers,
            "gpu_enabled": self.gpu_enabled,
            "custom_thresholds": self.custom_thresholds,
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "workers": self.server.workers,
                "timeout": self.server.timeout,
                "max_request_size": self.server.max_request_size,
            },
            "storage": {
                "result_dir": self.storage.result_dir,
                "sample_dir": self.storage.sample_dir,
                "keep_days": self.storage.keep_days,
                "save_thumbnails": self.storage.save_thumbnails,
                "thumbnail_size": list(self.storage.thumbnail_size),
            },
            "log": {
                "level": self.log.level,
                "format": self.log.format,
                "file": self.log.file,
                "max_size": self.log.max_size,
                "backup_count": self.log.backup_count,
            },
            "sample_collection": {
                "enabled": self.sample_collection.enabled,
                "collect_abnormal": self.sample_collection.collect_abnormal,
                "collect_boundary": self.sample_collection.collect_boundary,
                "boundary_range": list(self.sample_collection.boundary_range),
                "max_samples_per_type": self.sample_collection.max_samples_per_type,
            },
        }

    def save(self, config_path: str) -> None:
        """保存配置到文件"""
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, default_flow_style=False)


# 全局配置实例
_global_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = AppConfig.load()
    return _global_config


def set_config(config: AppConfig) -> None:
    """设置全局配置实例"""
    global _global_config
    _global_config = config


def reload_config(config_path: Optional[str] = None) -> AppConfig:
    """重新加载配置"""
    global _global_config
    _global_config = AppConfig.load(config_path)
    return _global_config

