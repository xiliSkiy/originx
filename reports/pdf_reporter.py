# -*- coding: utf-8 -*-
"""
PDF 报告生成器
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .base import BaseReporter, ReportData


class PdfReporter(BaseReporter):
    """PDF 报告生成器"""
    
    format = "pdf"
    extension = ".pdf"
    
    # 问题类型中文名
    ISSUE_NAMES = {
        "normal": "正常",
        "blur": "图像模糊",
        "over_bright": "过度曝光",
        "under_bright": "曝光不足",
        "low_contrast": "对比度过低",
        "high_contrast": "对比度过高",
        "color_cast": "色彩偏差",
        "desaturated": "色彩饱和度低",
        "noise": "噪声干扰",
        "stripe": "条纹干扰",
        "occlusion": "画面遮挡",
        "signal_loss": "信号丢失",
        "freeze": "画面冻结",
        "scene_change": "场景变换异常",
        "shake": "视频抖动",
    }
    
    def __init__(self):
        """初始化 PDF 报告生成器"""
        self._register_fonts()
    
    def _register_fonts(self):
        """注册中文字体"""
        # 尝试注册常用中文字体
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "/System/Library/Fonts/STHeiti Light.ttc",  # macOS
            "C:\\Windows\\Fonts\\msyh.ttc",  # Windows
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
        ]
        
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    pdfmetrics.registerFont(TTFont("Chinese", font_path))
                    self.chinese_font = "Chinese"
                    return
                except Exception:
                    continue
        
        # 如果没有找到中文字体，使用默认字体
        self.chinese_font = "Helvetica"
    
    def generate(self, data: ReportData, output_path: str) -> str:
        """生成 PDF 报告"""
        output_file = self._ensure_output_dir(output_path)
        output_file = output_file.with_suffix(self.extension)
        
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # 标题样式
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontName=self.chinese_font,
            fontSize=20,
            spaceAfter=20,
            alignment=1,  # 居中
        )
        
        # 正文样式
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName=self.chinese_font,
            fontSize=10,
            spaceAfter=6,
        )
        
        # 小标题样式
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontName=self.chinese_font,
            fontSize=14,
            spaceBefore=16,
            spaceAfter=12,
        )
        
        # 标题
        story.append(Paragraph(data.title, title_style))
        story.append(Paragraph(
            f"生成时间: {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            body_style
        ))
        story.append(Spacer(1, 12))
        
        # 摘要信息
        story.append(Paragraph("检测摘要", heading_style))
        
        summary_data = [
            ["指标", "数值"],
            ["检测总数", str(data.total_count)],
            ["正常数量", str(data.normal_count)],
            ["异常数量", str(data.abnormal_count)],
            ["异常率", f"{data.abnormal_rate:.1f}%"],
        ]
        
        summary_table = Table(summary_data, colWidths=[100, 100])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#409EFF')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F7FA')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DCDFE6')),
        ]))
        story.append(summary_table)
        
        # 异常详情
        if data.abnormal_count > 0:
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"异常详情 ({data.abnormal_count}项)", heading_style))
            
            abnormal_data = [["文件名", "主要问题", "严重程度", "耗时(ms)"]]
            
            for r in data.get_abnormal_results()[:20]:  # 最多显示20条
                filename = r.get("image_path") or r.get("video_path") or "-"
                # 截断长文件名
                if len(filename) > 30:
                    filename = "..." + filename[-27:]
                
                issue = self.ISSUE_NAMES.get(r.get("primary_issue", ""), r.get("primary_issue", "-"))
                severity = r.get("severity", "-")
                process_time = r.get("total_process_time_ms") or r.get("process_time_ms") or 0
                
                abnormal_data.append([
                    filename,
                    issue,
                    severity,
                    f"{process_time:.1f}",
                ])
            
            abnormal_table = Table(abnormal_data, colWidths=[150, 80, 60, 60])
            abnormal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#409EFF')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FEF0F0')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DCDFE6')),
            ]))
            story.append(abnormal_table)
        
        doc.build(story)
        return str(output_file)

