# -*- coding: utf-8 -*-
"""
报告导出 CLI 命令
"""

import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from reports import ReportService

console = Console()


@click.group(name="report")
def report_group():
    """报告管理命令组"""
    pass


@report_group.command(name="export")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--format", "-f", "formats", multiple=True, default=["json", "html"],
              help="输出格式 (可多选: json, html, excel, pdf)")
@click.option("--output", "-o", default=None, help="输出路径（不含扩展名）")
@click.option("--title", "-t", default="检测报告", help="报告标题")
def export_report(input_file: str, formats: tuple, output: str, title: str):
    """
    从 JSON 结果文件导出报告
    
    示例:
        originx report export result.json -f excel -f pdf
    """
    # 读取输入文件
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 提取结果
    if isinstance(data, list):
        results = data
    elif "results" in data:
        results = data["results"]
    else:
        console.print("[red]无效的结果文件格式[/red]")
        return
    
    console.print(f"\n[bold blue]📄 导出报告[/bold blue]")
    console.print(f"   输入: {input_file}")
    console.print(f"   结果数: {len(results)}")
    console.print(f"   格式: {', '.join(formats)}")
    console.print()
    
    # 生成报告
    service = ReportService()
    generated = service.generate_report(
        results=results,
        formats=list(formats),
        title=title,
        output_path=output,
    )
    
    if generated:
        console.print("[green]✓ 报告生成成功:[/green]")
        for fmt, path in generated.items():
            console.print(f"   {fmt.upper()}: {path}")
    else:
        console.print("[red]报告生成失败[/red]")


@report_group.command(name="formats")
def list_formats():
    """列出支持的报告格式"""
    formats = ReportService.get_available_formats()
    
    table = Table(title="支持的报告格式")
    table.add_column("格式", style="cyan")
    table.add_column("扩展名")
    table.add_column("说明")
    
    format_info = {
        "json": (".json", "JSON 格式，适合程序处理"),
        "html": (".html", "HTML 网页，适合在线查看"),
        "excel": (".xlsx", "Excel 表格，适合数据分析"),
        "pdf": (".pdf", "PDF 文档，适合正式报告"),
    }
    
    for fmt in formats:
        ext, desc = format_info.get(fmt, ("", ""))
        table.add_row(fmt, ext, desc)
    
    console.print(table)

