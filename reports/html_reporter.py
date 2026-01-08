# -*- coding: utf-8 -*-
"""
HTML 报告生成器
"""

from pathlib import Path
from jinja2 import Template

from .base import BaseReporter, ReportData


# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            color: #303133;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 24px; margin-bottom: 10px; }
        .header .time { opacity: 0.8; font-size: 14px; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        .stat-card .value { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
        .stat-card .label { color: #909399; font-size: 14px; }
        .stat-card.primary .value { color: #409eff; }
        .stat-card.success .value { color: #67c23a; }
        .stat-card.warning .value { color: #e6a23c; }
        .stat-card.danger .value { color: #f56c6c; }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        .card h2 { font-size: 18px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #ebeef5; }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ebeef5; }
        th { background: #f5f7fa; font-weight: 600; }
        tr:hover { background: #fafafa; }
        
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .status.normal { background: rgba(103,194,58,0.1); color: #67c23a; }
        .status.abnormal { background: rgba(245,108,108,0.1); color: #f56c6c; }
        
        .issue-list { list-style: none; }
        .issue-list li {
            padding: 12px 16px;
            margin-bottom: 8px;
            background: #fef0f0;
            border-radius: 8px;
            border-left: 4px solid #f56c6c;
        }
        .issue-list li strong { color: #f56c6c; }
        
        @media (max-width: 800px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <div class="time">生成时间: {{ timestamp }}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card primary">
                <div class="value">{{ total_count }}</div>
                <div class="label">检测总数</div>
            </div>
            <div class="stat-card success">
                <div class="value">{{ normal_count }}</div>
                <div class="label">正常数量</div>
            </div>
            <div class="stat-card danger">
                <div class="value">{{ abnormal_count }}</div>
                <div class="label">异常数量</div>
            </div>
            <div class="stat-card warning">
                <div class="value">{{ "%.1f"|format(abnormal_rate) }}%</div>
                <div class="label">异常率</div>
            </div>
        </div>
        
        {% if abnormal_results %}
        <div class="card">
            <h2>⚠️ 异常详情 ({{ abnormal_count }}项)</h2>
            <table>
                <thead>
                    <tr>
                        <th>文件名</th>
                        <th>主要问题</th>
                        <th>严重程度</th>
                        <th>耗时</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in abnormal_results %}
                    <tr>
                        <td>{{ r.image_path or r.video_path or '-' }}</td>
                        <td>{{ issue_names.get(r.primary_issue, r.primary_issue) }}</td>
                        <td><span class="status abnormal">{{ severity_names.get(r.severity, r.severity) }}</span></td>
                        <td>{{ "%.1f"|format(r.total_process_time_ms or r.process_time_ms or 0) }}ms</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}
        
        <div class="card">
            <h2>📊 全部结果</h2>
            <table>
                <thead>
                    <tr>
                        <th>文件名</th>
                        <th>状态</th>
                        <th>主要问题</th>
                        <th>耗时</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in results %}
                    <tr>
                        <td>{{ r.image_path or r.video_path or '-' }}</td>
                        <td>
                            <span class="status {{ 'abnormal' if r.is_abnormal else 'normal' }}">
                                {{ '异常' if r.is_abnormal else '正常' }}
                            </span>
                        </td>
                        <td>{{ issue_names.get(r.primary_issue, r.primary_issue or '-') }}</td>
                        <td>{{ "%.1f"|format(r.total_process_time_ms or r.process_time_ms or 0) }}ms</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


class HtmlReporter(BaseReporter):
    """HTML 报告生成器"""
    
    format = "html"
    extension = ".html"
    
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
    
    SEVERITY_NAMES = {
        "normal": "正常",
        "info": "提示",
        "warning": "警告",
        "error": "严重",
    }
    
    def generate(self, data: ReportData, output_path: str) -> str:
        """生成 HTML 报告"""
        output_file = self._ensure_output_dir(output_path)
        output_file = output_file.with_suffix(self.extension)
        
        template = Template(HTML_TEMPLATE)
        html = template.render(
            title=data.title,
            timestamp=data.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            total_count=data.total_count,
            normal_count=data.normal_count,
            abnormal_count=data.abnormal_count,
            abnormal_rate=data.abnormal_rate,
            results=data.results,
            abnormal_results=data.get_abnormal_results(),
            issue_names=self.ISSUE_NAMES,
            severity_names=self.SEVERITY_NAMES,
        )
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        
        return str(output_file)

