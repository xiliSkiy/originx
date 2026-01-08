# -*- coding: utf-8 -*-
"""
批量检测任务执行器
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from scheduler.models import ScheduledTask, TaskExecution
from services.diagnosis_service import DiagnosisService

logger = logging.getLogger(__name__)


def batch_detect_job(task: ScheduledTask, execution: TaskExecution) -> Dict[str, Any]:
    """
    批量检测任务执行器
    
    Args:
        task: 任务配置
        execution: 执行记录
        
    Returns:
        执行结果统计
    """
    config = task.config
    output = task.output
    
    input_path = Path(config.get("input_path", "."))
    pattern = config.get("pattern", "*.jpg")
    recursive = config.get("recursive", True)
    profile = config.get("profile", "normal")
    level = config.get("level", "standard")
    
    # 查找图像文件
    if recursive:
        image_files = list(input_path.rglob(pattern))
    else:
        image_files = list(input_path.glob(pattern))
    
    if not image_files:
        logger.warning(f"未找到匹配的图像文件: {input_path}/{pattern}")
        return {
            "total": 0,
            "normal": 0,
            "abnormal": 0,
        }
    
    logger.info(f"找到 {len(image_files)} 个图像文件")
    
    # 执行检测
    service = DiagnosisService()
    results = []
    normal_count = 0
    abnormal_count = 0
    
    for image_file in image_files:
        try:
            result = service.diagnose_image(str(image_file), profile=profile, level=level)
            results.append(result.to_dict())
            
            if result.is_abnormal:
                abnormal_count += 1
            else:
                normal_count += 1
                
        except Exception as e:
            logger.error(f"检测失败: {image_file}, 错误: {e}")
    
    # 生成报告
    report_path = None
    output_path = Path(output.get("path", "./reports"))
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_path / f"batch_{task.id}_{timestamp}.json"
    
    report = {
        "task_id": task.id,
        "task_name": task.name,
        "execution_id": execution.id,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "normal_count": normal_count,
            "abnormal_count": abnormal_count,
        },
        "results": results,
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    report_path = str(report_file)
    logger.info(f"报告已保存: {report_path}")
    
    return {
        "total": len(results),
        "normal": normal_count,
        "abnormal": abnormal_count,
        "report_path": report_path,
    }

