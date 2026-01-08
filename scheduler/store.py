# -*- coding: utf-8 -*-
"""
任务存储
"""

import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .models import ScheduledTask, TaskExecution

logger = logging.getLogger(__name__)


class TaskStore:
    """任务存储（基于YAML文件）"""
    
    def __init__(self, file_path: Path):
        """
        初始化存储
        
        Args:
            file_path: 存储文件路径
        """
        self.file_path = Path(file_path)
        self._ensure_file()
    
    def _ensure_file(self):
        """确保文件存在"""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_data({"tasks": [], "executions": []})
    
    def _read_data(self) -> Dict[str, Any]:
        """读取数据"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {"tasks": [], "executions": []}
        except Exception as e:
            logger.error(f"读取数据失败: {e}")
            return {"tasks": [], "executions": []}
    
    def _write_data(self, data: Dict[str, Any]):
        """写入数据"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            logger.error(f"写入数据失败: {e}")
    
    # 任务操作
    
    def save_task(self, task: ScheduledTask):
        """保存任务"""
        data = self._read_data()
        tasks = data.get("tasks", [])
        
        # 查找是否已存在
        found = False
        for i, t in enumerate(tasks):
            if t.get("id") == task.id:
                tasks[i] = task.to_dict()
                found = True
                break
        
        if not found:
            tasks.append(task.to_dict())
        
        data["tasks"] = tasks
        self._write_data(data)
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        data = self._read_data()
        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                return ScheduledTask.from_dict(t)
        return None
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """获取所有任务"""
        data = self._read_data()
        return [ScheduledTask.from_dict(t) for t in data.get("tasks", [])]
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        data = self._read_data()
        tasks = data.get("tasks", [])
        
        new_tasks = [t for t in tasks if t.get("id") != task_id]
        
        if len(new_tasks) < len(tasks):
            data["tasks"] = new_tasks
            self._write_data(data)
            return True
        
        return False
    
    # 执行记录操作
    
    def save_execution(self, execution: TaskExecution):
        """保存执行记录"""
        data = self._read_data()
        executions = data.get("executions", [])
        
        # 查找是否已存在
        found = False
        for i, e in enumerate(executions):
            if e.get("id") == execution.id:
                executions[i] = execution.to_dict()
                found = True
                break
        
        if not found:
            executions.insert(0, execution.to_dict())  # 新记录放在前面
        
        # 限制记录数量
        if len(executions) > 1000:
            executions = executions[:1000]
        
        data["executions"] = executions
        self._write_data(data)
    
    def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """获取执行记录"""
        data = self._read_data()
        for e in data.get("executions", []):
            if e.get("id") == execution_id:
                return TaskExecution.from_dict(e)
        return None
    
    def get_executions(
        self,
        task_id: Optional[str] = None,
        limit: int = 50
    ) -> List[TaskExecution]:
        """获取执行记录列表"""
        data = self._read_data()
        executions = data.get("executions", [])
        
        if task_id:
            executions = [e for e in executions if e.get("task_id") == task_id]
        
        return [TaskExecution.from_dict(e) for e in executions[:limit]]

