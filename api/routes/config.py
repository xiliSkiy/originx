"""配置接口"""

from typing import List

from fastapi import APIRouter, HTTPException

from config import (
    AppConfig,
    get_config,
    set_config,
    PRESET_PROFILES,
)
from ..schemas.request import UpdateConfigRequest, UpdateThresholdsRequest
from ..schemas.response import (
    BaseResponse,
    ConfigResponse,
    ConfigData,
    ProfileListResponse,
    ProfileInfo,
    ThresholdsInfo,
)

router = APIRouter()


def thresholds_to_info(config: AppConfig) -> ThresholdsInfo:
    """将配置转换为阈值信息"""
    thresholds = config.get_thresholds()
    return ThresholdsInfo(
        blur_threshold=thresholds.blur_threshold,
        brightness_min=thresholds.brightness_min,
        brightness_max=thresholds.brightness_max,
        contrast_min=thresholds.contrast_min,
        saturation_min=thresholds.saturation_min,
        color_cast_threshold=thresholds.color_cast_threshold,
        noise_threshold=thresholds.noise_threshold,
        stripe_threshold=thresholds.stripe_threshold,
    )


@router.get("", response_model=ConfigResponse, summary="获取当前配置")
async def get_current_config():
    """获取当前系统配置"""
    config = get_config()

    data = ConfigData(
        profile=config.profile,
        detection_level=config.detection_level,
        parallel_detection=config.parallel_detection,
        max_workers=config.max_workers,
        gpu_enabled=config.gpu_enabled,
        thresholds=thresholds_to_info(config),
    )

    return ConfigResponse(code=0, message="success", data=data)


@router.put("", response_model=ConfigResponse, summary="更新配置")
async def update_config(request: UpdateConfigRequest):
    """更新系统配置"""
    config = get_config()

    # 更新配置
    if request.profile is not None:
        if request.profile not in PRESET_PROFILES:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40005,
                    "message": "Invalid profile name",
                    "details": f"有效的配置模板: {list(PRESET_PROFILES.keys())}",
                },
            )
        config.profile = request.profile

    if request.detection_level is not None:
        if request.detection_level not in ["fast", "standard", "deep"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40006,
                    "message": "Invalid detection level",
                    "details": "有效的检测级别: fast, standard, deep",
                },
            )
        config.detection_level = request.detection_level

    if request.parallel_detection is not None:
        config.parallel_detection = request.parallel_detection

    if request.max_workers is not None:
        config.max_workers = max(1, min(request.max_workers, 16))

    if request.custom_thresholds is not None:
        config.custom_thresholds = request.custom_thresholds

    # 更新全局配置
    set_config(config)

    data = ConfigData(
        profile=config.profile,
        detection_level=config.detection_level,
        parallel_detection=config.parallel_detection,
        max_workers=config.max_workers,
        gpu_enabled=config.gpu_enabled,
        thresholds=thresholds_to_info(config),
    )

    return ConfigResponse(code=0, message="success", data=data)


@router.get("/profiles", response_model=ProfileListResponse, summary="获取所有配置模板")
async def get_profiles():
    """获取所有可用的配置模板"""
    profiles = []

    for name, profile in PRESET_PROFILES.items():
        thresholds = ThresholdsInfo(
            blur_threshold=profile.thresholds.blur_threshold,
            brightness_min=profile.thresholds.brightness_min,
            brightness_max=profile.thresholds.brightness_max,
            contrast_min=profile.thresholds.contrast_min,
            saturation_min=profile.thresholds.saturation_min,
            color_cast_threshold=profile.thresholds.color_cast_threshold,
            noise_threshold=profile.thresholds.noise_threshold,
            stripe_threshold=profile.thresholds.stripe_threshold,
        )

        profiles.append(
            ProfileInfo(
                name=profile.name,
                display_name=profile.display_name,
                description=profile.description,
                thresholds=thresholds,
            )
        )

    return ProfileListResponse(code=0, message="success", data=profiles)


@router.get("/profiles/{name}", response_model=BaseResponse, summary="获取指定配置模板")
async def get_profile(name: str):
    """获取指定的配置模板"""
    if name not in PRESET_PROFILES:
        raise HTTPException(
            status_code=404,
            detail={
                "code": 40005,
                "message": "Profile not found",
                "details": f"有效的配置模板: {list(PRESET_PROFILES.keys())}",
            },
        )

    profile = PRESET_PROFILES[name]
    thresholds = ThresholdsInfo(
        blur_threshold=profile.thresholds.blur_threshold,
        brightness_min=profile.thresholds.brightness_min,
        brightness_max=profile.thresholds.brightness_max,
        contrast_min=profile.thresholds.contrast_min,
        saturation_min=profile.thresholds.saturation_min,
        color_cast_threshold=profile.thresholds.color_cast_threshold,
        noise_threshold=profile.thresholds.noise_threshold,
        stripe_threshold=profile.thresholds.stripe_threshold,
    )

    data = ProfileInfo(
        name=profile.name,
        display_name=profile.display_name,
        description=profile.description,
        thresholds=thresholds,
    )

    return BaseResponse(code=0, message="success", data=data.model_dump())


@router.get("/thresholds", response_model=BaseResponse, summary="获取当前阈值")
async def get_thresholds():
    """获取当前检测阈值"""
    config = get_config()
    thresholds = thresholds_to_info(config)

    return BaseResponse(code=0, message="success", data=thresholds.model_dump())


@router.put("/thresholds", response_model=BaseResponse, summary="更新阈值")
async def update_thresholds(request: UpdateThresholdsRequest):
    """更新检测阈值"""
    config = get_config()

    # 更新自定义阈值
    if config.custom_thresholds is None:
        config.custom_thresholds = {}

    if request.blur_threshold is not None:
        config.custom_thresholds["blur_threshold"] = request.blur_threshold
    if request.brightness_min is not None:
        config.custom_thresholds["brightness_min"] = request.brightness_min
    if request.brightness_max is not None:
        config.custom_thresholds["brightness_max"] = request.brightness_max
    if request.contrast_min is not None:
        config.custom_thresholds["contrast_min"] = request.contrast_min
    if request.saturation_min is not None:
        config.custom_thresholds["saturation_min"] = request.saturation_min
    if request.color_cast_threshold is not None:
        config.custom_thresholds["color_cast_threshold"] = request.color_cast_threshold
    if request.noise_threshold is not None:
        config.custom_thresholds["noise_threshold"] = request.noise_threshold
    if request.stripe_threshold is not None:
        config.custom_thresholds["stripe_threshold"] = request.stripe_threshold

    set_config(config)

    thresholds = thresholds_to_info(config)

    return BaseResponse(code=0, message="success", data=thresholds.model_dump())


@router.post("/profiles/{name}/apply", response_model=ConfigResponse, summary="应用配置模板")
async def apply_profile(name: str):
    """应用指定的配置模板"""
    if name not in PRESET_PROFILES:
        raise HTTPException(
            status_code=404,
            detail={
                "code": 40005,
                "message": "Profile not found",
                "details": f"有效的配置模板: {list(PRESET_PROFILES.keys())}",
            },
        )
    
    config = get_config()
    config.profile = name
    set_config(config)
    
    data = ConfigData(
        profile=config.profile,
        detection_level=config.detection_level,
        parallel_detection=config.parallel_detection,
        max_workers=config.max_workers,
        gpu_enabled=config.gpu_enabled,
        thresholds=thresholds_to_info(config),
    )
    
    return ConfigResponse(code=0, message="success", data=data)

