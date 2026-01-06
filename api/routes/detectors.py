"""检测器接口"""

from typing import List

from fastapi import APIRouter, HTTPException

from core import DetectorRegistry
from ..schemas.response import (
    DetectorListResponse,
    DetectorInfoResponse,
    DetectorInfo,
)

router = APIRouter()


@router.get("", response_model=DetectorListResponse, summary="获取所有检测器")
async def list_detectors():
    """获取所有已注册的检测器列表"""
    detector_list = DetectorRegistry.list_detectors()

    detectors = [
        DetectorInfo(
            name=d["name"],
            display_name=d["display_name"],
            description=d["description"],
            version=d["version"],
            priority=d["priority"],
            supported_levels=d["supported_levels"],
            suppresses=d.get("suppresses", []),
        )
        for d in detector_list
    ]

    return DetectorListResponse(code=0, message="success", data=detectors)


@router.get("/{name}", response_model=DetectorInfoResponse, summary="获取检测器详情")
async def get_detector(name: str):
    """获取指定检测器的详细信息"""
    info = DetectorRegistry.get_detector_info(name)

    if info is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": 40404,
                "message": "Detector not found",
                "details": f"检测器 '{name}' 不存在",
            },
        )

    detector = DetectorInfo(
        name=info["name"],
        display_name=info["display_name"],
        description=info["description"],
        version=info["version"],
        priority=info["priority"],
        supported_levels=info["supported_levels"],
        suppresses=info.get("suppresses", []),
    )

    return DetectorInfoResponse(code=0, message="success", data=detector)

