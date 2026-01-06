"""Pydantic模型"""

from .request import (
    DiagnoseImageRequest,
    DiagnoseBatchRequest,
    UpdateConfigRequest,
    UpdateThresholdsRequest,
)
from .response import (
    BaseResponse,
    DiagnoseResponse,
    BatchDiagnoseResponse,
    ConfigResponse,
    DetectorListResponse,
    DetectorInfoResponse,
    HealthResponse,
    SystemInfoResponse,
)

__all__ = [
    # Request
    "DiagnoseImageRequest",
    "DiagnoseBatchRequest",
    "UpdateConfigRequest",
    "UpdateThresholdsRequest",
    # Response
    "BaseResponse",
    "DiagnoseResponse",
    "BatchDiagnoseResponse",
    "ConfigResponse",
    "DetectorListResponse",
    "DetectorInfoResponse",
    "HealthResponse",
    "SystemInfoResponse",
]

