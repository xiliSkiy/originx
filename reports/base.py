# -*- coding: utf-8 -*-
"""
报告生成器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class ReportData:
    """报告数据"""
    title: str = "检测报告"
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 摘要信息
    summary: Dict[str, Any] = field(default_factory=dict)
    
    # 检测结果
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_count(self) -> int:
        return len(self.results)
    
    @property
    def normal_count(self) -> int:
        return sum(1 for r in self.results if not r.get("is_abnormal", False))
    
    @property
    def abnormal_count(self) -> int:
        return sum(1 for r in self.results if r.get("is_abnormal", False))
    
    @property
    def abnormal_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.abnormal_count / self.total_count * 100
    
    def get_abnormal_results(self) -> List[Dict[str, Any]]:
        """获取异常结果"""
        return [r for r in self.results if r.get("is_abnormal", False)]
    
    def get_issue_distribution(self) -> Dict[str, int]:
        """获取问题类型分布"""
        distribution = {}
        for r in self.results:
            if r.get("is_abnormal"):
                issue_type = r.get("primary_issue", "unknown")
                distribution[issue_type] = distribution.get(issue_type, 0) + 1
        return distribution


class BaseReporter(ABC):
    """报告生成器基类"""
    
    # 报告格式
    format: str = "base"
    extension: str = ""
    
    @abstractmethod
    def generate(self, data: ReportData, output_path: str) -> str:
        """
        生成报告
        
        Args:
            data: 报告数据
            output_path: 输出路径（不含扩展名）
            
        Returns:
            生成的报告文件路径
        """
        pass
    
    def _ensure_output_dir(self, output_path: str) -> Path:
        """确保输出目录存在"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

