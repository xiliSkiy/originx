"""CLI入口"""

import click
from rich.console import Console

from .commands import detect, serve, config, benchmark, video, task, report

console = Console()


@click.group()
@click.version_option(version="1.5.0", prog_name="OriginX")
def cli():
    """
    OriginX - 图像/视频质量诊断系统

    使用 --help 查看各命令的详细帮助
    """
    pass


# 注册命令
cli.add_command(detect.detect)
cli.add_command(serve.serve)
cli.add_command(config.config)
cli.add_command(benchmark.benchmark)
cli.add_command(video.video_group)
cli.add_command(task.task_group)
cli.add_command(report.report_group)


@cli.command()
def info():
    """显示系统信息"""
    import sys
    import cv2

    # 导入检测器
    import core.detectors  # noqa
    import core.detectors.video  # noqa
    from core import DetectorRegistry
    from core.detectors.video import FreezeDetector, SceneChangeDetector, ShakeDetector

    console.print("\n[bold blue]OriginX - 图像/视频质量诊断系统[/bold blue]\n")
    console.print(f"  版本: [green]1.5.0[/green]")
    console.print(f"  Python: [green]{sys.version.split()[0]}[/green]")
    console.print(f"  OpenCV: [green]{cv2.__version__}[/green]")

    # GPU信息
    try:
        gpu_count = cv2.cuda.getCudaEnabledDeviceCount()
        console.print(f"  GPU: [green]可用 ({gpu_count} 设备)[/green]")
    except Exception:
        console.print(f"  GPU: [yellow]不可用[/yellow]")

    # 图像检测器信息
    image_detectors = DetectorRegistry.list_detectors()
    console.print(f"\n  [bold]图像检测器:[/bold] [green]{len(image_detectors)}[/green]")
    for d in image_detectors:
        console.print(f"    - {d['display_name']} ({d['name']})")

    # 视频检测器信息
    video_detectors = [
        FreezeDetector,
        SceneChangeDetector,
        ShakeDetector,
    ]
    console.print(f"\n  [bold]视频检测器:[/bold] [green]{len(video_detectors)}[/green]")
    for detector_cls in video_detectors:
        console.print(f"    - {detector_cls.display_name} ({detector_cls.name})")

    console.print(f"\n  [bold]总计:[/bold] [green]{len(image_detectors) + len(video_detectors)}[/green] 个检测器")
    console.print()


@cli.command()
@click.argument("detector_name", required=False)
def detectors(detector_name: str = None):
    """列出检测器信息"""
    # 导入检测器
    import core.detectors  # noqa
    import core.detectors.video  # noqa
    from core import DetectorRegistry
    from core.detectors.video import FreezeDetector, SceneChangeDetector, ShakeDetector
    from rich.table import Table

    if detector_name:
        # 显示单个检测器详情
        # 先尝试从图像检测器查找
        info = DetectorRegistry.get_detector_info(detector_name)
        
        # 如果没找到，尝试从视频检测器查找
        if info is None:
            video_detectors_map = {
                "freeze": FreezeDetector,
                "scene_change": SceneChangeDetector,
                "shake": ShakeDetector,
            }
            if detector_name in video_detectors_map:
                detector_cls = video_detectors_map[detector_name]
                console.print(f"\n[bold]{detector_cls.display_name}[/bold]")
                console.print(f"  名称: {detector_cls.name}")
                console.print(f"  版本: {detector_cls.version if hasattr(detector_cls, 'version') else '1.0.0'}")
                console.print(f"  描述: {detector_cls.description}")
                console.print(f"  类型: 视频检测器")
                console.print()
                return
            else:
                console.print(f"[red]检测器 '{detector_name}' 不存在[/red]")
                return

        console.print(f"\n[bold]{info['display_name']}[/bold]")
        console.print(f"  名称: {info['name']}")
        console.print(f"  版本: {info['version']}")
        console.print(f"  描述: {info['description']}")
        console.print(f"  优先级: {info['priority']}")
        console.print(f"  支持级别: {', '.join(info['supported_levels'])}")
        if info.get('suppresses'):
            console.print(f"  抑制: {', '.join(info['suppresses'])}")
        console.print()
    else:
        # 列出所有检测器（图像 + 视频）
        image_detectors = DetectorRegistry.list_detectors()
        video_detectors = [
            FreezeDetector,
            SceneChangeDetector,
            ShakeDetector,
        ]

        # 图像检测器表格
        if image_detectors:
            table = Table(title="图像检测器")
            table.add_column("名称", style="cyan")
            table.add_column("显示名", style="green")
            table.add_column("优先级")
            table.add_column("支持级别")
            table.add_column("版本")

            for d in image_detectors:
                table.add_row(
                    d["name"],
                    d["display_name"],
                    str(d["priority"]),
                    ", ".join(d["supported_levels"]),
                    d["version"],
                )
            console.print(table)
            console.print()

        # 视频检测器表格
        if video_detectors:
            video_table = Table(title="视频检测器")
            video_table.add_column("名称", style="cyan")
            video_table.add_column("显示名", style="green")
            video_table.add_column("版本")

            for detector_cls in video_detectors:
                version = getattr(detector_cls, 'version', '1.0.0')
                video_table.add_row(
                    detector_cls.name,
                    detector_cls.display_name,
                    version,
                )
            console.print(video_table)
            console.print()

        # 总计
        total = len(image_detectors) + len(video_detectors)
        console.print(f"[bold]总计: {total} 个检测器[/bold] (图像: {len(image_detectors)}, 视频: {len(video_detectors)})")


if __name__ == "__main__":
    cli()

