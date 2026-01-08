# -*- coding: utf-8 -*-
"""
视频诊断 API 路由
"""

import os
import time
import tempfile
import logging
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from api.schemas.video import (
    VideoDiagnoseRequest,
    VideoDiagnoseResponse,
    VideoBatchDiagnoseRequest,
    VideoBatchDiagnoseResponse,
    VideoDetectorInfo,
    VideoDetectionResultResponse,
    VideoSegmentResponse,
    VideoIssueResponse,
)
from services.video_service import VideoService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/video", tags=["视频诊断"])


def _result_to_response(result) -> VideoDiagnoseResponse:
    """将诊断结果转换为响应模型"""
    return VideoDiagnoseResponse(
        video_path=result.video_path,
        video_id=result.video_id,
        width=result.width,
        height=result.height,
        fps=result.fps,
        duration=result.duration,
        frame_count=result.frame_count,
        sampled_frames=result.sampled_frames,
        is_abnormal=result.is_abnormal,
        overall_score=result.overall_score,
        primary_issue=result.primary_issue,
        severity=result.severity,
        issues=[
            VideoIssueResponse(
                issue_type=issue.issue_type,
                severity=issue.severity,
                start_time=issue.start_time,
                end_time=issue.end_time,
                duration=issue.duration,
                confidence=issue.confidence,
                description=issue.description,
            )
            for issue in result.issues
        ],
        detection_results=[
            VideoDetectionResultResponse(
                detector_name=dr.detector_name,
                is_abnormal=dr.is_abnormal,
                score=dr.score,
                threshold=dr.threshold,
                confidence=dr.confidence,
                issue_type=dr.issue_type,
                severity=dr.severity,
                segments=[
                    VideoSegmentResponse(
                        start_frame=seg.start_frame,
                        end_frame=seg.end_frame,
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        duration=seg.duration,
                        confidence=seg.confidence,
                        metadata=seg.metadata,
                    )
                    for seg in dr.segments
                ],
                explanation=dr.explanation,
                suggestions=dr.suggestions,
                possible_causes=dr.possible_causes,
                evidence=dr.evidence,
                process_time_ms=dr.process_time_ms,
                frames_analyzed=dr.frames_analyzed,
            )
            for dr in result.detection_results
        ],
        process_time_ms=result.process_time_ms,
    )


@router.post("/diagnose", response_model=VideoDiagnoseResponse)
async def diagnose_video(
    video: UploadFile = File(..., description="视频文件"),
    profile: str = Form(default="normal", description="配置模板"),
    detectors: Optional[str] = Form(default=None, description="检测器列表（逗号分隔）"),
    sample_strategy: str = Form(default="interval", description="采样策略"),
    sample_interval: float = Form(default=1.0, description="采样间隔"),
    max_frames: int = Form(default=300, description="最大采样帧数"),
):
    """
    诊断上传的视频文件
    """
    # 保存上传的视频到临时文件
    suffix = Path(video.filename).suffix if video.filename else ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await video.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # 解析检测器列表
        detector_list = None
        if detectors:
            detector_list = [d.strip() for d in detectors.split(",")]
        
        # 创建服务并诊断
        service = VideoService(
            sample_strategy=sample_strategy,
            sample_interval=sample_interval,
            max_frames=max_frames,
        )
        result = service.diagnose_video(
            video_path=tmp_path,
            detectors=detector_list,
            profile=profile,
        )
        
        # 替换临时路径为原始文件名
        result.video_path = video.filename or "uploaded_video"
        
        return _result_to_response(result)
        
    except Exception as e:
        logger.exception(f"视频诊断失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/diagnose/path", response_model=VideoDiagnoseResponse)
async def diagnose_video_by_path(
    video_path: str = Form(..., description="视频文件路径"),
    profile: str = Form(default="normal", description="配置模板"),
    detectors: Optional[str] = Form(default=None, description="检测器列表（逗号分隔）"),
    sample_strategy: str = Form(default="interval", description="采样策略"),
    sample_interval: float = Form(default=1.0, description="采样间隔"),
    max_frames: int = Form(default=300, description="最大采样帧数"),
):
    """
    诊断指定路径的视频文件
    """
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"视频文件不存在: {video_path}")
    
    try:
        # 解析检测器列表
        detector_list = None
        if detectors:
            detector_list = [d.strip() for d in detectors.split(",")]
        
        # 创建服务并诊断
        service = VideoService(
            sample_strategy=sample_strategy,
            sample_interval=sample_interval,
            max_frames=max_frames,
        )
        result = service.diagnose_video(
            video_path=video_path,
            detectors=detector_list,
            profile=profile,
        )
        
        return _result_to_response(result)
        
    except Exception as e:
        logger.exception(f"视频诊断失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagnose/batch", response_model=VideoBatchDiagnoseResponse)
async def diagnose_videos_batch(request: VideoBatchDiagnoseRequest):
    """
    批量诊断视频文件
    """
    start_time = time.time()
    
    # 验证文件路径
    for path in request.video_paths:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"视频文件不存在: {path}")
    
    try:
        service = VideoService()
        results = service.diagnose_batch(
            video_paths=request.video_paths,
            detectors=request.detectors,
            profile=request.profile,
        )
        
        # 统计结果
        success = sum(1 for r in results if r.overall_score > 0)
        failed = len(results) - success
        normal_count = sum(1 for r in results if not r.is_abnormal)
        abnormal_count = sum(1 for r in results if r.is_abnormal)
        
        return VideoBatchDiagnoseResponse(
            total=len(results),
            success=success,
            failed=failed,
            normal_count=normal_count,
            abnormal_count=abnormal_count,
            results=[_result_to_response(r) for r in results],
            process_time_ms=(time.time() - start_time) * 1000,
        )
        
    except Exception as e:
        logger.exception(f"批量视频诊断失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detectors", response_model=List[VideoDetectorInfo])
async def list_video_detectors():
    """
    获取可用的视频检测器列表
    """
    service = VideoService()
    detectors = service.get_available_detectors()
    return [VideoDetectorInfo(**d) for d in detectors]

