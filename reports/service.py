# -*- coding: utf-8 -*-
"""
报告服务
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseReporter, ReportData
from .json_reporter import JsonReporter
from .html_reporter import HtmlReporter
from .excel_reporter import ExcelReporter
from .pdf_reporter import PdfReporter

logger = logging.getLogger(__name__)


class ReportService:
    """报告服务"""
    
    # 支持的报告格式
    REPORTERS: Dict[str, type] = {
        "json": JsonReporter,
        "html": HtmlReporter,
        "excel": ExcelReporter,
        "pdf": PdfReporter,
    }
    
    def __init__(self, output_dir: str = "./reports"):
        """
        初始化报告服务
        
        Args:
            output_dir: 默认输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(
        self,
        results: List[Dict[str, Any]],
        formats: List[str] = None,
        title: str = "检测报告",
        output_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        生成报告
        
        Args:
            results: 检测结果列表
            formats: 输出格式列表，默认为 ["json", "html"]
            title: 报告标题
            output_path: 输出路径（不含扩展名），默认使用时间戳
            metadata: 附加元数据
            
        Returns:
            生成的报告文件路径字典 {格式: 文件路径}
        """
        if formats is None:
            formats = ["json", "html"]
        
        # 生成默认输出路径
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"report_{timestamp}")
        
        # 构建报告数据
        data = ReportData(
            title=title,
            timestamp=datetime.now(),
            results=results,
            metadata=metadata or {},
        )
        
        # 生成各格式报告
        generated = {}
        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in self.REPORTERS:
                logger.warning(f"不支持的报告格式: {fmt}")
                continue
            
            try:
                reporter = self.REPORTERS[fmt]()
                file_path = reporter.generate(data, output_path)
                generated[fmt] = file_path
                logger.info(f"生成 {fmt.upper()} 报告: {file_path}")
            except Exception as e:
                logger.error(f"生成 {fmt.upper()} 报告失败: {e}")
        
        return generated
    
    @classmethod
    def get_available_formats(cls) -> List[str]:
        """获取支持的报告格式"""
        return list(cls.REPORTERS.keys())

