"""诊断接口"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import get_config
from core import DetectorRegistry, DiagnosisPipeline, DetectionLevel
from core.utils.image_utils import load_image, load_image_from_base64, load_image_from_url
from ..schemas.request import DiagnoseImageRequest, DiagnoseBatchRequest
from ..schemas.response import (
    DiagnoseResponse,
    DiagnoseData,
    BatchDiagnoseResponse,
    BatchDiagnoseData,
    BatchSummary,
    IssueDetail,
    MetaInfo,
)

router = APIRouter()


def generate_task_id(prefix: str = "img") -> str:
    """生成任务ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{unique_id}"


def result_to_response(result, task_id: str, return_evidence: bool = True) -> DiagnoseData:
    """将诊断结果转换为响应数据"""
    issues = []
    for det_result in result.detection_results:
        issue = IssueDetail(
            type=det_result.issue_type,
            is_abnormal=det_result.is_abnormal,
            score=round(det_result.score, 4),
            threshold=det_result.threshold,
            confidence=round(det_result.confidence, 4),
            severity=det_result.severity.value,
            explanation=det_result.explanation,
            possible_causes=det_result.possible_causes,
            suggestions=det_result.suggestions,
            evidence=det_result.evidence if return_evidence else None,
        )
        issues.append(issue)

    return DiagnoseData(
        task_id=task_id,
        is_abnormal=result.is_abnormal,
        primary_issue=result.primary_issue,
        severity=result.severity.value,
        scores={k: round(v, 4) for k, v in result.scores.items()},
        issues=issues,
        suppressed_issues=result.suppressed_issues,
        image_info={
            "width": result.image_size[0],
            "height": result.image_size[1],
        },
    )


@router.post("/image", response_model=DiagnoseResponse, summary="单图诊断（同步）")
async def diagnose_image(
    file: Optional[UploadFile] = File(None),
    image: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    profile: str = Form(default="normal"),
    level: str = Form(default="standard"),
    detectors: Optional[str] = Form(default=None),
    return_evidence: bool = Form(default=True),
):
    """
    对单张图像进行质量诊断

    支持三种方式上传图像：
    - 文件上传 (file)
    - Base64编码 (image)
    - URL地址 (image_url)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"开始处理图像诊断请求: file={file.filename if file else None}, profile={profile}, level={level}")
    
    try:
        task_id = generate_task_id()

        # 加载图像
        img = None
        if file is not None:
            # 检查文件是否为空
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 40008,
                        "message": "File name is required",
                        "details": "上传的文件必须包含文件名",
                    },
                )
            
            contents = await file.read()
            if not contents or len(contents) == 0:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 40009,
                        "message": "File is empty",
                        "details": "上传的文件为空",
                    },
                )
            
            import numpy as np
            import cv2

            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                logger.error(f"无法解码图像文件，文件名: {file.filename}, 文件大小: {len(contents)} bytes")
                # 尝试检查文件头
                file_header = contents[:16] if len(contents) >= 16 else contents
                logger.error(f"文件头: {file_header.hex()}")
        elif image is not None:
            img = load_image_from_base64(image)
        elif image_url is not None:
            img = load_image_from_url(image_url)

        if img is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 40007,
                    "message": "Image decode failed",
                    "details": "无法解析图像，请检查图像格式或URL是否正确",
                },
            )

        # 获取配置
        config = get_config()
        threshold_config = config.get_threshold_dict()
        threshold_config["profile"] = profile
        threshold_config["parallel_detection"] = config.parallel_detection
        threshold_config["max_workers"] = config.max_workers

        # 创建流水线
        pipeline = DiagnosisPipeline(threshold_config)

        # 解析检测级别
        detection_level = DetectionLevel.from_string(level)

        # 解析检测器列表
        detector_list = None
        if detectors:
            detector_list = [d.strip() for d in detectors.split(",")]

        # 执行诊断
        result = pipeline.diagnose(
            image=img,
            level=detection_level,
            detectors=detector_list,
            image_id=task_id,
        )

        # 构建响应
        data = result_to_response(result, task_id, return_evidence)
        meta = MetaInfo(
            process_time_ms=round(result.total_process_time_ms, 2),
            detection_level=result.detection_level.name,
            profile=profile,
            version="1.5.0",
            timestamp=result.timestamp,
        )

        return DiagnoseResponse(code=0, message="success", data=data, meta=meta)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"图像诊断失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50001,
                "message": "Internal server error",
                "details": f"诊断过程中发生错误: {str(e)}",
            },
        )


@router.post("/image/json", response_model=DiagnoseResponse, summary="单图诊断（JSON请求）")
async def diagnose_image_json(request: DiagnoseImageRequest):
    """
    对单张图像进行质量诊断（JSON请求方式）
    """
    task_id = generate_task_id()

    # 加载图像
    img = None
    if request.image:
        img = load_image_from_base64(request.image)
    elif request.image_url:
        img = load_image_from_url(request.image_url)

    if img is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": 40007,
                "message": "Image decode failed",
                "details": "无法解析图像，请检查Base64编码或URL是否正确",
            },
        )

    # 获取配置
    config = get_config()
    threshold_config = config.get_threshold_dict()
    threshold_config["profile"] = request.profile
    threshold_config["parallel_detection"] = config.parallel_detection
    threshold_config["max_workers"] = config.max_workers

    # 创建流水线
    pipeline = DiagnosisPipeline(threshold_config)

    # 解析检测级别
    detection_level = DetectionLevel.from_string(request.level)

    # 执行诊断
    result = pipeline.diagnose(
        image=img,
        level=detection_level,
        detectors=request.detectors,
        image_id=task_id,
    )

    # 构建响应
    data = result_to_response(result, task_id, request.return_evidence)
    meta = MetaInfo(
        process_time_ms=round(result.total_process_time_ms, 2),
        detection_level=result.detection_level.name,
        profile=request.profile,
        version="1.5.0",
        timestamp=result.timestamp,
    )

    return DiagnoseResponse(code=0, message="success", data=data, meta=meta)


@router.post("/batch", response_model=BatchDiagnoseResponse, summary="批量诊断")
async def diagnose_batch(request: DiagnoseBatchRequest):
    """
    批量诊断多张图像
    """
    task_id = generate_task_id(prefix="batch")
    start_time = datetime.now()

    # 获取配置
    config = get_config()
    threshold_config = config.get_threshold_dict()
    threshold_config["profile"] = request.profile
    threshold_config["parallel_detection"] = config.parallel_detection
    threshold_config["max_workers"] = config.max_workers

    # 创建流水线
    pipeline = DiagnosisPipeline(threshold_config)
    detection_level = DetectionLevel.from_string(request.level)

    results = []
    abnormal_count = 0
    issue_distribution: dict = {}

    for item in request.images:
        # 加载图像
        img = None
        if item.url:
            img = load_image_from_url(item.url)
        elif item.base64:
            img = load_image_from_base64(item.base64)
        elif item.path:
            img = load_image(item.path)

        if img is None:
            # 跳过无法加载的图像
            continue

        # 执行诊断
        result = pipeline.diagnose(
            image=img,
            level=detection_level,
            detectors=request.detectors,
            image_id=item.id,
        )

        # 统计
        if result.is_abnormal:
            abnormal_count += 1
            if result.primary_issue:
                issue_distribution[result.primary_issue] = (
                    issue_distribution.get(result.primary_issue, 0) + 1
                )

        results.append(result_to_response(result, item.id, return_evidence=False))

    # 计算总耗时
    total_time = (datetime.now() - start_time).total_seconds() * 1000

    # 构建响应
    summary = BatchSummary(
        total_images=len(results),
        abnormal_count=abnormal_count,
        normal_count=len(results) - abnormal_count,
        issue_distribution=issue_distribution,
    )

    data = BatchDiagnoseData(
        task_id=task_id,
        status="completed",
        progress={
            "total": len(request.images),
            "processed": len(results),
            "abnormal": abnormal_count,
        },
        results=results,
        summary=summary,
    )

    meta = MetaInfo(
        process_time_ms=round(total_time, 2),
        detection_level=detection_level.name,
        profile=request.profile,
        version="1.5.0",
        timestamp=datetime.now().isoformat(),
    )

    return BatchDiagnoseResponse(code=0, message="success", data=data, meta=meta)

