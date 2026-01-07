"""诊断命令"""

import json
import os
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group()
def detect():
    """图像/视频诊断命令"""
    pass


@detect.command("image")
@click.argument("path", type=click.Path(exists=True))
@click.option("-p", "--profile", default="normal", help="配置模板 (strict/normal/loose)")
@click.option("-l", "--level", default="standard", help="检测级别 (fast/standard/deep)")
@click.option("-o", "--output", type=click.Path(), help="输出文件路径")
@click.option("-f", "--format", "output_format", default="table", help="输出格式 (table/json/simple)")
@click.option("-d", "--detectors", help="指定检测器 (逗号分隔)")
@click.option("-v", "--verbose", is_flag=True, help="详细输出")
def detect_image(
    path: str,
    profile: str,
    level: str,
    output: Optional[str],
    output_format: str,
    detectors: Optional[str],
    verbose: bool,
):
    """
    对单张图像进行质量诊断

    示例:
        originx detect image ./test.jpg
        originx detect image ./test.jpg -p strict -l deep
        originx detect image ./test.jpg -d blur,brightness -o result.json
    """
    import cv2

    # 导入模块
    import core.detectors  # noqa
    from core import DiagnosisPipeline, DetectionLevel
    from config import AppConfig, set_config

    # 加载配置
    config = AppConfig()
    config.profile = profile
    set_config(config)

    # 加载图像
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("加载图像...", total=None)
        image = cv2.imread(path)
        progress.update(task, description="图像加载完成")

    if image is None:
        console.print(f"[red]无法加载图像: {path}[/red]")
        return

    # 创建流水线
    threshold_config = config.get_threshold_dict()
    threshold_config["profile"] = profile
    threshold_config["parallel_detection"] = config.parallel_detection
    threshold_config["max_workers"] = config.max_workers

    pipeline = DiagnosisPipeline(threshold_config)
    detection_level = DetectionLevel.from_string(level)

    # 解析检测器
    detector_list = None
    if detectors:
        detector_list = [d.strip() for d in detectors.split(",")]

    # 执行诊断
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("正在诊断...", total=None)
        result = pipeline.diagnose(
            image=image,
            level=detection_level,
            detectors=detector_list,
            image_path=path,
        )
        progress.update(task, description="诊断完成")

    # 输出结果
    if output_format == "json":
        output_json(result, output, verbose)
    elif output_format == "simple":
        output_simple(result)
    else:
        output_table(result, verbose)


def output_table(result, verbose: bool):
    """表格格式输出"""
    # 总体状态
    status = "[green]正常[/green]" if not result.is_abnormal else "[red]异常[/red]"
    severity_colors = {
        "normal": "green",
        "info": "blue",
        "warning": "yellow",
        "critical": "red",
    }
    severity_color = severity_colors.get(result.severity.value, "white")

    console.print()
    console.print(Panel(
        f"诊断状态: {status}\n"
        f"严重程度: [{severity_color}]{result.severity.value}[/{severity_color}]\n"
        f"主要问题: {result.primary_issue or '无'}\n"
        f"处理耗时: {result.total_process_time_ms:.2f}ms",
        title="诊断结果",
    ))

    # 详细结果表格
    table = Table(title="检测详情")
    table.add_column("检测器", style="cyan")
    table.add_column("状态")
    table.add_column("得分")
    table.add_column("阈值")
    table.add_column("置信度")
    table.add_column("严重程度")

    for det_result in result.detection_results:
        status = "[green]正常[/green]" if not det_result.is_abnormal else "[red]异常[/red]"
        severity_color = severity_colors.get(det_result.severity.value, "white")

        table.add_row(
            det_result.detector_name,
            status,
            f"{det_result.score:.2f}",
            f"{det_result.threshold:.2f}",
            f"{det_result.confidence:.2f}",
            f"[{severity_color}]{det_result.severity.value}[/{severity_color}]",
        )

    console.print(table)

    # 显示问题详情
    if result.is_abnormal:
        console.print("\n[bold]问题分析:[/bold]")
        for det_result in result.detection_results:
            if det_result.is_abnormal:
                console.print(f"\n  [yellow]{det_result.explanation}[/yellow]")

                if det_result.possible_causes:
                    console.print("  可能原因:")
                    for cause in det_result.possible_causes:
                        console.print(f"    • {cause}")

                if det_result.suggestions:
                    console.print("  建议措施:")
                    for suggestion in det_result.suggestions:
                        console.print(f"    • {suggestion}")

    # 详细证据
    if verbose:
        console.print("\n[bold]详细数据:[/bold]")
        for det_result in result.detection_results:
            console.print(f"\n  {det_result.detector_name}:")
            for key, value in det_result.evidence.items():
                if isinstance(value, float):
                    console.print(f"    {key}: {value:.4f}")
                else:
                    console.print(f"    {key}: {value}")

    console.print()


def output_simple(result):
    """简单格式输出"""
    status = "PASS" if not result.is_abnormal else "FAIL"
    console.print(f"{status} | {result.severity.value} | {result.primary_issue or 'OK'} | {result.total_process_time_ms:.2f}ms")


def output_json(result, output_path: Optional[str], verbose: bool):
    """JSON格式输出"""
    data = result.to_dict()

    if not verbose:
        # 移除详细证据
        for det in data.get("detection_results", []):
            det.pop("evidence", None)

    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        console.print(f"[green]结果已保存到: {output_path}[/green]")
    else:
        console.print(json_str)


@detect.command("batch")
@click.argument("directory", type=click.Path(exists=True))
@click.option("-p", "--profile", default="normal", help="配置模板")
@click.option("-l", "--level", default="fast", help="检测级别")
@click.option("--pattern", default="*.jpg,*.png,*.jpeg", help="文件匹配模式")
@click.option("-r", "--recursive", is_flag=True, help="递归子目录")
@click.option("-o", "--output", type=click.Path(), help="输出目录")
@click.option("--report", is_flag=True, help="生成汇总报告")
def detect_batch(
    directory: str,
    profile: str,
    level: str,
    pattern: str,
    recursive: bool,
    output: Optional[str],
    report: bool,
):
    """
    批量诊断目录下的图像

    示例:
        originx detect batch ./images/
        originx detect batch ./images/ -r -o ./results/ --report
    """
    import cv2
    from glob import glob

    # 导入模块
    import core.detectors  # noqa
    from core import DiagnosisPipeline, DetectionLevel
    from config import AppConfig, set_config

    # 加载配置
    config = AppConfig()
    config.profile = profile
    set_config(config)

    # 收集文件
    patterns = pattern.split(",")
    files = []
    base_path = Path(directory)

    for p in patterns:
        p = p.strip()
        if recursive:
            files.extend(base_path.rglob(p))
        else:
            files.extend(base_path.glob(p))

    files = sorted(set(files))

    if not files:
        console.print(f"[yellow]未找到匹配的文件[/yellow]")
        return

    console.print(f"找到 [green]{len(files)}[/green] 个文件")

    # 创建流水线
    threshold_config = config.get_threshold_dict()
    threshold_config["profile"] = profile
    threshold_config["parallel_detection"] = config.parallel_detection
    threshold_config["max_workers"] = config.max_workers

    pipeline = DiagnosisPipeline(threshold_config)
    detection_level = DetectionLevel.from_string(level)

    # 创建输出目录
    if output:
        os.makedirs(output, exist_ok=True)

    # 统计
    results = []
    abnormal_count = 0
    issue_counts = {}

    # 批量处理
    with Progress(console=console) as progress:
        task = progress.add_task("诊断中...", total=len(files))

        for file_path in files:
            image = cv2.imread(str(file_path))
            if image is None:
                progress.advance(task)
                continue

            result = pipeline.diagnose(
                image=image,
                level=detection_level,
                image_path=str(file_path),
            )

            results.append(result)

            if result.is_abnormal:
                abnormal_count += 1
                if result.primary_issue:
                    issue_counts[result.primary_issue] = issue_counts.get(result.primary_issue, 0) + 1

            progress.advance(task)

    # 输出汇总
    console.print()
    console.print(Panel(
        f"总数: [green]{len(results)}[/green]\n"
        f"正常: [green]{len(results) - abnormal_count}[/green]\n"
        f"异常: [red]{abnormal_count}[/red]",
        title="诊断汇总",
    ))

    if issue_counts:
        console.print("\n问题分布:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
            console.print(f"  {issue}: {count}")

    # 保存报告
    if report and output:
        # 将 image_path 转换为相对于输出目录的相对路径
        output_path = Path(output).resolve()
        results_data = []
        for r in results:
            result_dict = r.to_dict()
            # 计算相对于输出目录的相对路径
            if result_dict.get("image_path"):
                image_abs_path = Path(result_dict["image_path"]).resolve()
                try:
                    relative_path = os.path.relpath(image_abs_path, output_path)
                    result_dict["image_path"] = relative_path.replace("\\", "/")
                except ValueError:
                    # Windows 跨驱动器时无法计算相对路径，保持原样
                    pass
            results_data.append(result_dict)

        report_data = {
            "summary": {
                "total": len(results),
                "normal": len(results) - abnormal_count,
                "abnormal": abnormal_count,
                "issue_distribution": issue_counts,
            },
            "results": results_data,
        }

        report_path = os.path.join(output, "report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        console.print(f"\n[green]报告已保存到: {report_path}[/green]")

    console.print()

