# -*- coding: utf-8 -*-
"""
定时任务调度服务
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from .models import ScheduledTask, TaskExecution, TaskType, TaskStatus
from .store import TaskStore

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务"""
    
    def __init__(self, store_path: str = "./data/scheduler"):
        """
        初始化调度服务
        
        Args:
            store_path: 任务存储路径
        """
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # 任务存储
        self.task_store = TaskStore(self.store_path / "tasks.yaml")
        self.execution_store = TaskStore(self.store_path / "executions.yaml")
        
        # 任务执行器映射
        self._job_executors: Dict[str, Callable] = {}
        
        # APScheduler 配置
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }
        
        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone='Asia/Shanghai'
        )
        
        # 注册默认执行器
        self._register_default_executors()
    
    def _register_default_executors(self):
        """注册默认任务执行器"""
        from .jobs import batch_detect_job, sample_detect_job, video_detect_job
        
        self._job_executors = {
            TaskType.BATCH.value: batch_detect_job,
            TaskType.SAMPLE.value: sample_detect_job,
            TaskType.VIDEO.value: video_detect_job,
        }
    
    def start(self):
        """启动调度器"""
        # 加载已有任务
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.enabled:
                self._add_job(task)
        
        self._scheduler.start()
        logger.info(f"调度器已启动，加载了 {len(tasks)} 个任务")
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        self._scheduler.shutdown(wait=wait)
        logger.info("调度器已关闭")
    
    def _add_job(self, task: ScheduledTask):
        """添加调度任务"""
        try:
            trigger = CronTrigger.from_crontab(task.cron_expression)
            
            self._scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task.id],
                id=task.id,
                name=task.name,
                replace_existing=True,
            )
            
            # 更新下次执行时间
            job = self._scheduler.get_job(task.id)
            if job and job.next_run_time:
                task.next_run_at = job.next_run_time
                self.task_store.save_task(task)
            
            logger.info(f"任务 {task.name} 已添加到调度器")
        except Exception as e:
            logger.error(f"添加任务 {task.name} 失败: {e}")
    
    def _remove_job(self, task_id: str):
        """移除调度任务"""
        try:
            self._scheduler.remove_job(task_id)
            logger.info(f"任务 {task_id} 已从调度器移除")
        except Exception as e:
            logger.warning(f"移除任务 {task_id} 失败: {e}")
    
    def _execute_task(self, task_id: str):
        """执行任务"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return
        
        # 创建执行记录
        execution = TaskExecution.create(task)
        execution.status = TaskStatus.RUNNING
        self.execution_store.save_execution(execution)
        
        try:
            # 获取执行器
            executor = self._job_executors.get(task.task_type.value)
            if not executor:
                raise ValueError(f"未知的任务类型: {task.task_type}")
            
            # 执行任务
            result = executor(task, execution)
            
            # 更新执行记录
            execution.total_items = result.get("total", 0)
            execution.normal_count = result.get("normal", 0)
            execution.abnormal_count = result.get("abnormal", 0)
            execution.report_path = result.get("report_path")
            execution.complete(success=True)
            
            logger.info(f"任务 {task.name} 执行成功")
            
        except Exception as e:
            execution.complete(success=False, error_message=str(e))
            logger.error(f"任务 {task.name} 执行失败: {e}")
        
        finally:
            # 更新任务状态
            task.last_run_at = execution.started_at
            job = self._scheduler.get_job(task_id)
            if job and job.next_run_time:
                task.next_run_at = job.next_run_time
            self.task_store.save_task(task)
            self.execution_store.save_execution(execution)
    
    # 任务管理 API
    
    def create_task(self, **kwargs) -> ScheduledTask:
        """创建任务"""
        task = ScheduledTask.create(**kwargs)
        self.task_store.save_task(task)
        
        if task.enabled:
            self._add_job(task)
        
        return task
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self.task_store.get_task(task_id)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """获取所有任务"""
        return self.task_store.get_all_tasks()
    
    def update_task(self, task_id: str, **kwargs) -> Optional[ScheduledTask]:
        """更新任务"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now()
        self.task_store.save_task(task)
        
        # 更新调度
        self._remove_job(task_id)
        if task.enabled:
            self._add_job(task)
        
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        self._remove_job(task_id)
        return self.task_store.delete_task(task_id)
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.enabled = True
        task.updated_at = datetime.now()
        self.task_store.save_task(task)
        self._add_job(task)
        return True
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.enabled = False
        task.updated_at = datetime.now()
        task.next_run_at = None
        self.task_store.save_task(task)
        self._remove_job(task_id)
        return True
    
    def run_task_now(self, task_id: str) -> Optional[TaskExecution]:
        """立即执行任务"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        # 在后台执行
        self._scheduler.add_job(
            func=self._execute_task,
            args=[task_id],
            id=f"{task_id}_manual",
            replace_existing=True,
        )
        
        return None  # 异步执行，不返回结果
    
    # 执行历史 API
    
    def get_executions(
        self,
        task_id: Optional[str] = None,
        limit: int = 50
    ) -> List[TaskExecution]:
        """获取执行历史"""
        return self.execution_store.get_executions(task_id=task_id, limit=limit)
    
    def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """获取执行记录"""
        return self.execution_store.get_execution(execution_id)

