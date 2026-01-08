# -*- coding: utf-8 -*-
"""
视频检测 CLI 命令
"""

import json
import time
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from services.video_service import VideoService

console = Console()


# 问题类型中文映射
ISSUE_TYPE_NAMES = {
    "normal": "正常",
    "freeze": "画面冻结",
    "scene_change": "场景变换",
    "shake": "视频抖动",
    "flicker": "频闪",
    "rolling": "滚屏",
}


def get_issue_type_name(issue_type: str) -> str:
    """获取问题类型的中文名称"""
    return ISSUE_TYPE_NAMES.get(issue_type, issue_type)


@click.group(name="video")
def video_group():
    """视频检测命令组"""
    pass


@video_group.command(name="detect")
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--profile", "-p", default="normal", 
              type=click.Choice(["strict", "normal", "loose"]),
              help="配置模板")
@click.option("--detectors", "-d", default=None,
              help="要使用的检测器（逗号分隔）")
@click.option("--sample-strategy", "-s", default="interval",
              type=click.Choice(["interval", "scene", "hybrid", "all"]),
              help="采样策略")
@click.option("--sample-interval", "-i", default=1.0, type=float,
              help="采样间隔（秒）")
@click.option("--max-frames", "-m", default=300, type=int,
              help="最大采样帧数")
@click.option("--output", "-o", default=None, type=click.Path(),
              help="结果输出文件路径")
@click.option("--format", "-f", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
def detect_video(
    video_path: str,
    profile: str,
    detectors: Optional[str],
    sample_strategy: str,
    sample_interval: float,
    max_frames: int,
    output: Optional[str],
    output_format: str,
):
    """检测单个视频文件"""
    
    # 解析检测器列表
    detector_list = None
    if detectors:
        detector_list = [d.strip() for d in detectors.split(",")]
    
    console.print(f"\n[bold blue]🎬 视频检测[/bold blue]")
    console.print(f"   文件: {video_path}")
    console.print(f"   配置: {profile}")
    console.print(f"   采样: {sample_strategy} (间隔 {sample_interval}s)")
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("正在分析视频...", total=None)
        
        try:
            service = VideoService(
                sample_strategy=sample_strategy,
                sample_interval=sample_interval,
                max_frames=max_frames,
            )
            result = service.diagnose_video(
                video_path=video_path,
                detectors=detector_list,
                profile=profile,
            )
            progress.update(task, completed=True)
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            raise click.Abort()
    
    # 输出结果
    if output_format == "json":
        result_dict = result.to_dict()
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            console.print(f"\n[green]✓ 结果已保存到: {output}[/green]")
        else:
            console.print_json(data=result_dict)
    else:
        _display_result_table(result)
    
    # 保存 JSON（如果指定了输出路径）
    if output and output_format != "json":
        result_dict = result.to_dict()
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        console.print(f"\n[green]✓ 结果已保存到: {output}[/green]")


def _display_result_table(result):
    """以表格形式显示结果"""
    # 基本信息
    status = "[red]⚠️ 异常[/red]" if result.is_abnormal else "[green]✅ 正常[/green]"
    
    info_table = Table(title="视频信息", show_header=False, box=None)
    info_table.add_column("key", style="dim")
    info_table.add_column("value")
    
    info_table.add_row("状态", status)
    info_table.add_row("分辨率", f"{result.width} × {result.height}")
    info_table.add_row("帧率", f"{result.fps:.2f} fps")
    info_table.add_row("时长", f"{result.duration:.2f} 秒")
    info_table.add_row("总帧数", str(result.frame_count))
    info_table.add_row("采样帧数", str(result.sampled_frames))
    info_table.add_row("整体评分", f"{result.overall_score:.1f}")
    info_table.add_row("处理耗时", f"{result.process_time_ms:.1f} ms")
    
    if result.primary_issue:
        info_table.add_row("主要问题", get_issue_type_name(result.primary_issue))
    
    console.print(Panel(info_table, title="📊 诊断结果"))
    
    # 检测器结果
    if result.detection_results:
        det_table = Table(title="检测器结果")
        det_table.add_column("检测器", style="cyan")
        det_table.add_column("状态")
        det_table.add_column("得分", justify="right")
        det_table.add_column("阈值", justify="right")
        det_table.add_column("问题数", justify="right")
        det_table.add_column("说明")
        
        for dr in result.detection_results:
            status_icon = "[red]⚠️[/red]" if dr.is_abnormal else "[green]✅[/green]"
            det_table.add_row(
                dr.detector_name,
                status_icon,
                f"{dr.score:.2f}",
                f"{dr.threshold:.2f}",
                str(len(dr.segments)),
                dr.explanation[:50] + "..." if len(dr.explanation) > 50 else dr.explanation,
            )
        
        console.print(det_table)
    
    # 问题列表
    if result.issues:
        issue_table = Table(title="问题详情")
        issue_table.add_column("类型", style="yellow")
        issue_table.add_column("严重度")
        issue_table.add_column("开始时间", justify="right")
        issue_table.add_column("结束时间", justify="right")
        issue_table.add_column("持续", justify="right")
        issue_table.add_column("置信度", justify="right")
        
        for issue in result.issues[:10]:  # 最多显示10个
            severity_color = {
                "normal": "green",
                "info": "blue",
                "warning": "yellow",
                "error": "red",
            }.get(issue.severity, "white")
            
            issue_table.add_row(
                get_issue_type_name(issue.issue_type),
                f"[{severity_color}]{issue.severity}[/{severity_color}]",
                f"{issue.start_time:.2f}s",
                f"{issue.end_time:.2f}s",
                f"{issue.duration:.2f}s",
                f"{issue.confidence:.0%}",
            )
        
        if len(result.issues) > 10:
            console.print(f"[dim]... 还有 {len(result.issues) - 10} 个问题[/dim]")
        
        console.print(issue_table)


@video_group.command(name="batch")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--pattern", "-P", default="*.mp4",
              help="文件匹配模式")
@click.option("--recursive", "-r", is_flag=True,
              help="递归搜索子目录")
@click.option("--profile", "-p", default="normal",
              type=click.Choice(["strict", "normal", "loose"]),
              help="配置模板")
@click.option("--output", "-o", default=None, type=click.Path(),
              help="结果输出目录")
def detect_batch(
    input_path: str,
    pattern: str,
    recursive: bool,
    profile: str,
    output: Optional[str],
):
    """批量检测视频文件"""
    
    input_dir = Path(input_path)
    
    # 查找视频文件
    if recursive:
        video_files = list(input_dir.rglob(pattern))
    else:
        video_files = list(input_dir.glob(pattern))
    
    if not video_files:
        console.print(f"[yellow]未找到匹配的视频文件: {pattern}[/yellow]")
        return
    
    console.print(f"\n[bold blue]🎬 批量视频检测[/bold blue]")
    console.print(f"   目录: {input_path}")
    console.print(f"   模式: {pattern}")
    console.print(f"   找到: {len(video_files)} 个视频")
    console.print()
    
    service = VideoService()
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("正在检测...", total=len(video_files))
        
        for video_file in video_files:
            try:
                result = service.diagnose_video(
                    video_path=str(video_file),
                    profile=profile,
                )
                results.append(result)
            except Exception as e:
                console.print(f"[red]  ✗ {video_file.name}: {e}[/red]")
            
            progress.update(task, advance=1)
    
    # 统计
    normal_count = sum(1 for r in results if not r.is_abnormal)
    abnormal_count = sum(1 for r in results if r.is_abnormal)
    
    console.print()
    console.print(f"[bold]检测完成:[/bold]")
    console.print(f"  总计: {len(results)}")
    console.print(f"  正常: [green]{normal_count}[/green]")
    console.print(f"  异常: [red]{abnormal_count}[/red]")
    
    # 保存结果
    if output:
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存汇总报告
        report = {
            "total": len(results),
            "normal_count": normal_count,
            "abnormal_count": abnormal_count,
            "results": [r.to_dict() for r in results],
        }
        
        report_path = output_dir / "report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        console.print(f"\n[green]✓ 报告已保存到: {report_path}[/green]")


@video_group.command(name="detectors")
def list_detectors():
    """列出可用的视频检测器"""
    service = VideoService()
    detectors = service.get_available_detectors()
    
    table = Table(title="可用视频检测器")
    table.add_column("名称", style="cyan")
    table.add_column("显示名称", style="green")
    table.add_column("描述")
    
    for d in detectors:
        table.add_row(d["name"], d["display_name"], d["description"])
    
    console.print(table)

