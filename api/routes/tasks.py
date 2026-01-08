# -*- coding: utf-8 -*-
"""
任务管理 API 路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas.task import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskResponse,
    TaskListResponse,
    ExecutionResponse,
    ExecutionListResponse,
)
from scheduler import SchedulerService, TaskType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["任务管理"])

# 全局调度服务实例
_scheduler: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """获取调度服务实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def _task_to_response(task) -> TaskResponse:
    """转换为响应模型"""
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        task_type=task.task_type.value,
        cron_expression=task.cron_expression,
        enabled=task.enabled,
        config=task.config,
        output=task.output,
        created_at=task.created_at.isoformat() if task.created_at else None,
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
        last_run_at=task.last_run_at.isoformat() if task.last_run_at else None,
        next_run_at=task.next_run_at.isoformat() if task.next_run_at else None,
    )


def _execution_to_response(execution) -> ExecutionResponse:
    """转换为响应模型"""
    return ExecutionResponse(
        id=execution.id,
        task_id=execution.task_id,
        task_name=execution.task_name,
        status=execution.status.value,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        finished_at=execution.finished_at.isoformat() if execution.finished_at else None,
        duration_seconds=execution.duration_seconds,
        total_items=execution.total_items,
        normal_count=execution.normal_count,
        abnormal_count=execution.abnormal_count,
        error_count=execution.error_count,
        report_path=execution.report_path,
        error_message=execution.error_message,
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks():
    """获取任务列表"""
    scheduler = get_scheduler()
    tasks = scheduler.get_all_tasks()
    
    return TaskListResponse(
        tasks=[_task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.post("", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """创建任务"""
    scheduler = get_scheduler()
    
    try:
        task_type = TaskType(request.task_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的任务类型: {request.task_type}")
    
    task = scheduler.create_task(
        name=request.name,
        description=request.description,
        task_type=task_type,
        cron_expression=request.cron_expression,
        enabled=request.enabled,
        config=request.config.model_dump(),
        output=request.output.model_dump(),
    )
    
    return _task_to_response(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    scheduler = get_scheduler()
    task = scheduler.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return _task_to_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, request: UpdateTaskRequest):
    """更新任务"""
    scheduler = get_scheduler()
    
    update_data = request.model_dump(exclude_unset=True)
    task = scheduler.update_task(task_id, **update_data)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return _task_to_response(task)


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    scheduler = get_scheduler()
    
    if not scheduler.delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return {"message": "删除成功"}


@router.post("/{task_id}/enable")
async def enable_task(task_id: str):
    """启用任务"""
    scheduler = get_scheduler()
    
    if not scheduler.enable_task(task_id):
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return {"message": "任务已启用"}


@router.post("/{task_id}/disable")
async def disable_task(task_id: str):
    """禁用任务"""
    scheduler = get_scheduler()
    
    if not scheduler.disable_task(task_id):
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return {"message": "任务已禁用"}


@router.post("/{task_id}/run")
async def run_task(task_id: str):
    """立即执行任务"""
    scheduler = get_scheduler()
    
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    scheduler.run_task_now(task_id)
    
    return {"message": "任务已开始执行"}


@router.get("/{task_id}/executions", response_model=ExecutionListResponse)
async def get_task_executions(
    task_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """获取任务执行历史"""
    scheduler = get_scheduler()
    
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    executions = scheduler.get_executions(task_id=task_id, limit=limit)
    
    return ExecutionListResponse(
        executions=[_execution_to_response(e) for e in executions],
        total=len(executions),
    )


@router.get("/executions/all", response_model=ExecutionListResponse)
async def get_all_executions(
    limit: int = Query(default=50, ge=1, le=200),
):
    """获取所有执行历史"""
    scheduler = get_scheduler()
    executions = scheduler.get_executions(limit=limit)
    
    return ExecutionListResponse(
        executions=[_execution_to_response(e) for e in executions],
        total=len(executions),
    )

