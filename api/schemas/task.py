# -*- coding: utf-8 -*-
"""
任务相关的请求/响应模型
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TaskConfigRequest(BaseModel):
    """任务配置"""
    input_path: str = Field(description="输入路径")
    pattern: str = Field(default="*.jpg", description="文件匹配模式")
    profile: str = Field(default="normal", description="配置模板")
    level: str = Field(default="standard", description="检测级别")
    recursive: bool = Field(default=True, description="是否递归搜索")
    sample_rate: Optional[float] = Field(default=None, description="抽样比例（抽样任务）")


class TaskOutputRequest(BaseModel):
    """输出配置"""
    path: str = Field(description="输出路径")
    format: List[str] = Field(default=["json"], description="输出格式")
    keep_days: int = Field(default=30, description="保留天数")


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    name: str = Field(description="任务名称")
    description: str = Field(default="", description="任务描述")
    task_type: str = Field(default="batch", description="任务类型: batch, sample, video")
    cron_expression: str = Field(description="Cron表达式")
    enabled: bool = Field(default=True, description="是否启用")
    config: TaskConfigRequest = Field(description="任务配置")
    output: TaskOutputRequest = Field(description="输出配置")


class UpdateTaskRequest(BaseModel):
    """更新任务请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    name: str
    description: str
    task_type: str
    cron_expression: str
    enabled: bool
    config: Dict[str, Any]
    output: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int


class ExecutionResponse(BaseModel):
    """执行记录响应"""
    id: str
    task_id: str
    task_name: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: float
    total_items: int
    normal_count: int
    abnormal_count: int
    error_count: int
    report_path: Optional[str] = None
    error_message: Optional[str] = None


class ExecutionListResponse(BaseModel):
    """执行记录列表响应"""
    executions: List[ExecutionResponse]
    total: int

