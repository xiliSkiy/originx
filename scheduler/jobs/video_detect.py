# -*- coding: utf-8 -*-
"""
视频检测任务执行器
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from scheduler.models import ScheduledTask, TaskExecution
from services.video_service import VideoService

logger = logging.getLogger(__name__)


def video_detect_job(task: ScheduledTask, execution: TaskExecution) -> Dict[str, Any]:
    """
    视频检测任务执行器
    
    Args:
        task: 任务配置
        execution: 执行记录
        
    Returns:
        执行结果统计
    """
    config = task.config
    output = task.output
    
    input_path = Path(config.get("input_path", "."))
    pattern = config.get("pattern", "*.mp4")
    recursive = config.get("recursive", True)
    profile = config.get("profile", "normal")
    
    # 视频特有配置
    sample_strategy = config.get("sample_strategy", "interval")
    sample_interval = config.get("sample_interval", 1.0)
    max_frames = config.get("max_frames", 300)
    
    # 查找视频文件
    if recursive:
        video_files = list(input_path.rglob(pattern))
    else:
        video_files = list(input_path.glob(pattern))
    
    if not video_files:
        logger.warning(f"未找到匹配的视频文件: {input_path}/{pattern}")
        return {
            "total": 0,
            "normal": 0,
            "abnormal": 0,
        }
    
    logger.info(f"找到 {len(video_files)} 个视频文件")
    
    # 执行检测
    service = VideoService(
        sample_strategy=sample_strategy,
        sample_interval=sample_interval,
        max_frames=max_frames,
    )
    
    results = []
    normal_count = 0
    abnormal_count = 0
    
    for video_file in video_files:
        try:
            result = service.diagnose_video(str(video_file), profile=profile)
            results.append(result.to_dict())
            
            if result.is_abnormal:
                abnormal_count += 1
            else:
                normal_count += 1
                
        except Exception as e:
            logger.error(f"检测失败: {video_file}, 错误: {e}")
    
    # 生成报告
    output_path = Path(output.get("path", "./reports"))
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_path / f"video_{task.id}_{timestamp}.json"
    
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

