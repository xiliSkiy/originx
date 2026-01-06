"""系统接口"""

import sys
import time
from datetime import datetime

import cv2

from fastapi import APIRouter

from core import DetectorRegistry
from ..schemas.response import (
    HealthResponse,
    HealthData,
    SystemInfoResponse,
    SystemInfoData,
)

router = APIRouter()

# 服务启动时间
_start_time = time.time()


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """
    健康检查接口

    用于检查服务是否正常运行
    """
    uptime = time.time() - _start_time
    detectors_count = DetectorRegistry.count()

    data = HealthData(
        status="healthy",
        uptime_seconds=round(uptime, 2),
        detectors_loaded=detectors_count,
    )

    return HealthResponse(code=0, message="success", data=data)


@router.get("/info", response_model=SystemInfoResponse, summary="系统信息")
async def system_info():
    """
    获取系统信息

    返回版本、依赖库版本等信息
    """
    # 检查GPU是否可用
    gpu_available = False
    try:
        # 尝试获取CUDA设备数量
        gpu_count = cv2.cuda.getCudaEnabledDeviceCount()
        gpu_available = gpu_count > 0
    except Exception:
        pass

    data = SystemInfoData(
        version="1.0.0",
        python_version=sys.version.split()[0],
        opencv_version=cv2.__version__,
        detectors_count=DetectorRegistry.count(),
        supported_formats=["JPEG", "PNG", "BMP", "TIFF", "WebP"],
        gpu_available=gpu_available,
    )

    return SystemInfoResponse(code=0, message="success", data=data)


@router.get("/metrics", summary="性能指标")
async def metrics():
    """
    获取性能指标

    返回服务运行状态和统计信息
    """
    import os
    import psutil

    process = psutil.Process(os.getpid())

    return {
        "code": 0,
        "message": "success",
        "data": {
            "uptime_seconds": round(time.time() - _start_time, 2),
            "memory_usage_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
            "thread_count": process.num_threads(),
            "detectors_loaded": DetectorRegistry.count(),
            "timestamp": datetime.now().isoformat(),
        },
    }

