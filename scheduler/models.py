# -*- coding: utf-8 -*-
"""
定时任务数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid


class TaskType(Enum):
    """任务类型"""
    BATCH = "batch"        # 批量检测
    SAMPLE = "sample"      # 抽样检测
    VIDEO = "video"        # 视频检测


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"        # 待执行
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


@dataclass
class ScheduledTask:
    """定时任务配置"""
    id: str                               # 任务ID
    name: str                             # 任务名称
    description: str = ""                 # 任务描述
    task_type: TaskType = TaskType.BATCH  # 任务类型
    cron_expression: str = "0 2 * * *"    # Cron 表达式
    enabled: bool = True                  # 是否启用
    
    # 检测配置
    config: Dict[str, Any] = field(default_factory=lambda: {
        "input_path": "/data/images/",
        "pattern": "*.jpg",
        "profile": "normal",
        "level": "standard",
        "recursive": True,
    })
    
    # 输出配置
    output: Dict[str, Any] = field(default_factory=lambda: {
        "path": "/data/reports/",
        "format": ["json", "html"],
        "keep_days": 30,
    })
    
    # 元数据
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    @classmethod
    def create(cls, name: str, **kwargs) -> "ScheduledTask":
        """创建新任务"""
        return cls(
            id=str(uuid.uuid4())[:8],
            name=name,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "cron_expression": self.cron_expression,
            "enabled": self.enabled,
            "config": self.config,
            "output": self.output,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """从字典创建"""
        task_type = TaskType(data.get("task_type", "batch"))
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            task_type=task_type,
            cron_expression=data.get("cron_expression", "0 2 * * *"),
            enabled=data.get("enabled", True),
            config=data.get("config", {}),
            output=data.get("output", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            last_run_at=datetime.fromisoformat(data["last_run_at"]) if data.get("last_run_at") else None,
            next_run_at=datetime.fromisoformat(data["next_run_at"]) if data.get("next_run_at") else None,
        )


@dataclass
class TaskExecution:
    """任务执行记录"""
    id: str                               # 执行ID
    task_id: str                          # 任务ID
    task_name: str                        # 任务名称
    status: TaskStatus = TaskStatus.PENDING
    
    # 执行时间
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # 统计信息
    total_items: int = 0                  # 总检测数
    normal_count: int = 0                 # 正常数
    abnormal_count: int = 0               # 异常数
    error_count: int = 0                  # 错误数
    
    # 结果文件
    report_path: Optional[str] = None
    
    # 错误信息
    error_message: Optional[str] = None
    
    @classmethod
    def create(cls, task: ScheduledTask) -> "TaskExecution":
        """创建执行记录"""
        return cls(
            id=str(uuid.uuid4())[:8],
            task_id=task.id,
            task_name=task.name,
            started_at=datetime.now(),
        )
    
    def complete(self, success: bool = True, error_message: str = None):
        """完成执行"""
        self.finished_at = datetime.now()
        self.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        if self.started_at:
            self.duration_seconds = (self.finished_at - self.started_at).total_seconds()
        if error_message:
            self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "total_items": self.total_items,
            "normal_count": self.normal_count,
            "abnormal_count": self.abnormal_count,
            "error_count": self.error_count,
            "report_path": self.report_path,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskExecution":
        """从字典创建"""
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            task_name=data["task_name"],
            status=TaskStatus(data.get("status", "pending")),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            finished_at=datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None,
            duration_seconds=data.get("duration_seconds", 0.0),
            total_items=data.get("total_items", 0),
            normal_count=data.get("normal_count", 0),
            abnormal_count=data.get("abnormal_count", 0),
            error_count=data.get("error_count", 0),
            report_path=data.get("report_path"),
            error_message=data.get("error_message"),
        )

