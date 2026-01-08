# -*- coding: utf-8 -*-
"""
JSON 报告生成器
"""

import json
from pathlib import Path

from .base import BaseReporter, ReportData


class JsonReporter(BaseReporter):
    """JSON 报告生成器"""
    
    format = "json"
    extension = ".json"
    
    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        """
        初始化 JSON 报告生成器
        
        Args:
            indent: 缩进空格数
            ensure_ascii: 是否使用 ASCII 编码
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
    
    def generate(self, data: ReportData, output_path: str) -> str:
        """生成 JSON 报告"""
        output_file = self._ensure_output_dir(output_path)
        output_file = output_file.with_suffix(self.extension)
        
        report = {
            "title": data.title,
            "timestamp": data.timestamp.isoformat(),
            "summary": {
                "total": data.total_count,
                "normal_count": data.normal_count,
                "abnormal_count": data.abnormal_count,
                "abnormal_rate": round(data.abnormal_rate, 2),
                **data.summary,
            },
            "issue_distribution": data.get_issue_distribution(),
            "metadata": data.metadata,
            "results": data.results,
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=self.ensure_ascii, indent=self.indent)
        
        return str(output_file)

