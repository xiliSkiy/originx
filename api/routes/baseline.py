# -*- coding: utf-8 -*-
"""
基准图像 API 路由
"""

import logging
import base64
import os
from typing import Optional, List
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, Field
import cv2
import numpy as np

from services.baseline_service import BaselineService
from services.diagnosis_service import DiagnosisService
from core.detectors.baseline_comparison_detector import BaselineComparisonDetector
from core.utils.image_utils import load_image_from_base64

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/baseline", tags=["baseline"])

# 全局服务实例
_baseline_service: Optional[BaselineService] = None
_diagnosis_service: Optional[DiagnosisService] = None


def get_baseline_service() -> BaselineService:
    """获取基准图像服务实例"""
    global _baseline_service
    if _baseline_service is None:
        _baseline_service = BaselineService()
    return _baseline_service


def get_diagnosis_service() -> DiagnosisService:
    """获取诊断服务实例"""
    global _diagnosis_service
    if _diagnosis_service is None:
        _diagnosis_service = DiagnosisService()
    return _diagnosis_service


class BaselineCreateRequest(BaseModel):
    """创建基准图像请求"""
    name: str = Field(..., description="名称")
    description: Optional[str] = Field(default=None, description="描述")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    image: Optional[str] = Field(default=None, description="Base64编码的图像")


class BaselineUpdateRequest(BaseModel):
    """更新基准图像请求"""
    name: Optional[str] = Field(default=None, description="名称")
    description: Optional[str] = Field(default=None, description="描述")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")


@router.post("/images")
async def create_baseline(
    name: str = Form(...),
    description: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
    image: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(default=None),
):
    """
    创建基准图像
    
    Args:
        name: 名称
        description: 描述
        tags: 标签（逗号分隔）
        image: 图像文件
        image_base64: Base64编码的图像
        
    Returns:
        创建的基准图像信息
    """
    try:
        service = get_baseline_service()
        
        # 解析标签
        tag_list = []
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        
        # 加载图像
        img = None
        if image:
            contents = await image.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif image_base64:
            img = load_image_from_base64(image_base64)
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40001,
                    "message": "Image is required",
                    "details": "必须提供图像文件或Base64编码的图像",
                },
            )
        
        if img is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40002,
                    "message": "Invalid image",
                    "details": "无法解码图像",
                },
            )
        
        baseline_id = service.save_baseline(
            image=img,
            name=name,
            description=description,
            tags=tag_list,
        )
        
        baseline = service.get_baseline(baseline_id)
        
        return {
            "baseline_id": baseline_id,
            "name": baseline["name"],
            "description": baseline["description"],
            "tags": baseline["tags"],
            "created_at": baseline["created_at"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create baseline: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50001,
                "message": "Failed to create baseline",
                "details": str(e),
            },
        )


@router.get("/images")
async def list_baselines():
    """
    列出所有基准图像
    
    Returns:
        基准图像列表
    """
    try:
        service = get_baseline_service()
        baselines = service.list_baselines()
        
        return {
            "baselines": baselines,
            "total": len(baselines),
        }
    except Exception as e:
        logger.error(f"Failed to list baselines: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50002,
                "message": "Failed to list baselines",
                "details": str(e),
            },
        )


@router.get("/images/{baseline_id}")
async def get_baseline(baseline_id: str):
    """
    获取基准图像信息
    
    Args:
        baseline_id: 基准图像ID
        
    Returns:
        基准图像信息
    """
    try:
        service = get_baseline_service()
        baseline = service.get_baseline(baseline_id)
        
        if not baseline:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40401,
                    "message": "Baseline not found",
                    "details": f"Baseline {baseline_id} not found",
                },
            )
        
        return baseline
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get baseline: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50003,
                "message": "Failed to get baseline",
                "details": str(e),
            },
        )


@router.get("/images/{baseline_id}/image")
async def get_baseline_image(baseline_id: str):
    """
    获取基准图像文件
    
    Args:
        baseline_id: 基准图像ID
        
    Returns:
        图像文件
    """
    from fastapi.responses import FileResponse
    
    try:
        service = get_baseline_service()
        baseline = service.get_baseline(baseline_id)
        
        if not baseline:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40401,
                    "message": "Baseline not found",
                    "details": f"Baseline {baseline_id} not found",
                },
            )
        
        image_path = baseline["image_path"]
        if not os.path.exists(image_path):
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40402,
                    "message": "Image file not found",
                    "details": f"Image file {image_path} not found",
                },
            )
        
        return FileResponse(image_path, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get baseline image: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50007,
                "message": "Failed to get baseline image",
                "details": str(e),
            },
        )


@router.delete("/images/{baseline_id}")
async def delete_baseline(baseline_id: str):
    """
    删除基准图像
    
    Args:
        baseline_id: 基准图像ID
        
    Returns:
        删除结果
    """
    try:
        service = get_baseline_service()
        success = service.delete_baseline(baseline_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40401,
                    "message": "Baseline not found",
                    "details": f"Baseline {baseline_id} not found",
                },
            )
        
        return {
            "baseline_id": baseline_id,
            "deleted": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete baseline: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50004,
                "message": "Failed to delete baseline",
                "details": str(e),
            },
        )


@router.put("/images/{baseline_id}")
async def update_baseline(
    baseline_id: str,
    request: BaselineUpdateRequest,
):
    """
    更新基准图像信息
    
    Args:
        baseline_id: 基准图像ID
        request: 更新请求
        
    Returns:
        更新后的基准图像信息
    """
    try:
        service = get_baseline_service()
        success = service.update_baseline(
            baseline_id=baseline_id,
            name=request.name,
            description=request.description,
            tags=request.tags,
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": 40401,
                    "message": "Baseline not found",
                    "details": f"Baseline {baseline_id} not found",
                },
            )
        
        baseline = service.get_baseline(baseline_id)
        return baseline
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update baseline: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50005,
                "message": "Failed to update baseline",
                "details": str(e),
            },
        )


@router.post("/compare")
async def compare_with_baseline(
    image: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(default=None),
    baseline_id: Optional[str] = Form(default=None),
    baseline_image: Optional[UploadFile] = File(None),
    baseline_image_base64: Optional[str] = Form(default=None),
    profile: str = Form(default="normal"),
    level: str = Form(default="standard"),
):
    """
    使用基准图像对比检测
    
    Args:
        image: 待检测图像
        image_base64: Base64编码的待检测图像
        baseline_id: 基准图像ID
        baseline_image: 基准图像文件
        baseline_image_base64: Base64编码的基准图像
        profile: 检测模板
        level: 检测级别
        
    Returns:
        对比检测结果
    """
    try:
        baseline_service = get_baseline_service()
        diagnosis_service = get_diagnosis_service()
        
        # 加载基准图像
        baseline_img = None
        if baseline_id:
            baseline_img = baseline_service.get_baseline_image(baseline_id)
            if baseline_img is None:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": 40401,
                        "message": "Baseline not found",
                        "details": f"Baseline {baseline_id} not found",
                    },
                )
        elif baseline_image:
            contents = await baseline_image.read()
            nparr = np.frombuffer(contents, np.uint8)
            baseline_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif baseline_image_base64:
            baseline_img = load_image_from_base64(baseline_image_base64)
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40001,
                    "message": "Baseline image is required",
                    "details": "必须提供基准图像ID、文件或Base64编码",
                },
            )
        
        # 加载待检测图像
        target_img = None
        if image:
            contents = await image.read()
            nparr = np.frombuffer(contents, np.uint8)
            target_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif image_base64:
            target_img = load_image_from_base64(image_base64)
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40002,
                    "message": "Target image is required",
                    "details": "必须提供待检测图像文件或Base64编码",
                },
            )
        
        if baseline_img is None or target_img is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40003,
                    "message": "Invalid image",
                    "details": "无法解码图像",
                },
            )
        
        # 执行基准对比检测
        baseline_detector = BaselineComparisonDetector(baseline_img)
        comparison_result = baseline_detector.detect(target_img)
        
        # 执行常规检测
        diagnosis_result = diagnosis_service.diagnose_image(
            image=target_img,
            level=level,
        )
        
        # 确保所有 NumPy 类型都转换为 Python 原生类型
        region_diffs = comparison_result.evidence.get("region_differences", [])
        # 递归转换 region_differences 中的 NumPy 类型
        def convert_numpy_types(obj):
            """递归转换 NumPy 类型为 Python 原生类型"""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_numpy_types(item) for item in obj]
            return obj
        
        region_diffs = convert_numpy_types(region_diffs)
        
        return {
            "task_id": diagnosis_result.image_id,
            "is_abnormal": bool(comparison_result.is_abnormal or diagnosis_result.is_abnormal),
            "overall_similarity": float(1.0 - comparison_result.score),
            "comparison_result": {
                "ssim_score": float(comparison_result.evidence.get("ssim_score", 0.0)),
                "histogram_similarity": float(comparison_result.evidence.get("histogram_similarity", 0.0)),
                "feature_match_score": float(comparison_result.evidence.get("feature_match_score", 0.0)),
                "region_differences": region_diffs,
            },
            "explanation": comparison_result.explanation,
            "suggestions": comparison_result.suggestions,
            "detection_results": [r.to_dict() for r in diagnosis_result.detection_results],
            "process_time_ms": float(comparison_result.process_time_ms + diagnosis_result.total_process_time_ms),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare with baseline: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50006,
                "message": "Failed to compare with baseline",
                "details": str(e),
            },
        )
