"""检测器注册表"""

from typing import Dict, List, Optional, Type, Any

from .base import BaseDetector, DetectionLevel


class DetectorRegistry:
    """检测器注册表 - 管理所有检测器的注册和获取"""

    _detectors: Dict[str, Type[BaseDetector]] = {}
    _instances: Dict[str, BaseDetector] = {}

    @classmethod
    def register(cls, detector_class: Type[BaseDetector]) -> Type[BaseDetector]:
        """
        注册检测器（可作为装饰器使用）

        示例:
            @DetectorRegistry.register
            class BlurDetector(BaseDetector):
                ...

        Args:
            detector_class: 检测器类

        Returns:
            Type[BaseDetector]: 检测器类（原样返回）
        """
        cls._detectors[detector_class.name] = detector_class
        return detector_class

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        取消注册检测器

        Args:
            name: 检测器名称

        Returns:
            bool: 是否成功取消注册
        """
        if name in cls._detectors:
            del cls._detectors[name]
            # 清除相关实例缓存
            keys_to_remove = [k for k in cls._instances if k.startswith(f"{name}_")]
            for key in keys_to_remove:
                del cls._instances[key]
            return True
        return False

    @classmethod
    def get(
        cls,
        name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[BaseDetector]:
        """
        获取检测器实例

        Args:
            name: 检测器名称
            config: 配置字典

        Returns:
            Optional[BaseDetector]: 检测器实例，不存在返回None
        """
        if name not in cls._detectors:
            return None

        # 生成缓存键
        config_hash = hash(str(sorted(config.items()))) if config else 0
        cache_key = f"{name}_{config_hash}"

        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls._detectors[name](config)

        return cls._instances[cache_key]

    @classmethod
    def get_all(
        cls,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[BaseDetector]:
        """
        获取所有已注册的检测器实例

        Args:
            config: 配置字典

        Returns:
            List[BaseDetector]: 检测器实例列表
        """
        detectors = []
        for name in cls._detectors:
            detector = cls.get(name, config)
            if detector:
                detectors.append(detector)
        return sorted(detectors, key=lambda d: d.priority)

    @classmethod
    def get_by_level(
        cls,
        level: DetectionLevel,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[BaseDetector]:
        """
        根据检测级别获取检测器

        Args:
            level: 检测级别
            config: 配置字典

        Returns:
            List[BaseDetector]: 支持该级别的检测器列表（按优先级排序）
        """
        detectors = []
        for name, detector_class in cls._detectors.items():
            if level in detector_class.supported_levels:
                detector = cls.get(name, config)
                if detector:
                    detectors.append(detector)
        return sorted(detectors, key=lambda d: d.priority)

    @classmethod
    def get_by_names(
        cls,
        names: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> List[BaseDetector]:
        """
        根据名称列表获取检测器

        Args:
            names: 检测器名称列表
            config: 配置字典

        Returns:
            List[BaseDetector]: 检测器列表
        """
        detectors = []
        for name in names:
            detector = cls.get(name, config)
            if detector:
                detectors.append(detector)
        return detectors

    @classmethod
    def list_detectors(cls) -> List[Dict[str, Any]]:
        """
        列出所有检测器信息

        Returns:
            List[Dict]: 检测器信息列表
        """
        return [
            {
                "name": detector_class.name,
                "display_name": detector_class.display_name,
                "description": detector_class.description,
                "version": detector_class.version,
                "priority": detector_class.priority,
                "supported_levels": [
                    level.name for level in detector_class.supported_levels
                ],
                "suppresses": detector_class.suppresses,
            }
            for detector_class in cls._detectors.values()
        ]

    @classmethod
    def get_detector_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        获取单个检测器信息

        Args:
            name: 检测器名称

        Returns:
            Optional[Dict]: 检测器信息，不存在返回None
        """
        if name not in cls._detectors:
            return None

        detector_class = cls._detectors[name]
        return {
            "name": detector_class.name,
            "display_name": detector_class.display_name,
            "description": detector_class.description,
            "version": detector_class.version,
            "priority": detector_class.priority,
            "supported_levels": [
                level.name for level in detector_class.supported_levels
            ],
            "suppresses": detector_class.suppresses,
        }

    @classmethod
    def clear_cache(cls) -> None:
        """清除实例缓存"""
        cls._instances.clear()

    @classmethod
    def clear_all(cls) -> None:
        """清除所有注册和缓存"""
        cls._detectors.clear()
        cls._instances.clear()

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        检查检测器是否已注册

        Args:
            name: 检测器名称

        Returns:
            bool: 是否已注册
        """
        return name in cls._detectors

    @classmethod
    def count(cls) -> int:
        """
        获取已注册检测器数量

        Returns:
            int: 检测器数量
        """
        return len(cls._detectors)

