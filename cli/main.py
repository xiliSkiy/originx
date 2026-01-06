"""CLI入口"""

import click
from rich.console import Console

from .commands import detect, serve, config, benchmark

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="OriginX")
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


@cli.command()
def info():
    """显示系统信息"""
    import sys
    import cv2

    # 导入检测器
    import core.detectors  # noqa
    from core import DetectorRegistry

    console.print("\n[bold blue]OriginX - 图像/视频质量诊断系统[/bold blue]\n")
    console.print(f"  版本: [green]1.0.0[/green]")
    console.print(f"  Python: [green]{sys.version.split()[0]}[/green]")
    console.print(f"  OpenCV: [green]{cv2.__version__}[/green]")

    # GPU信息
    try:
        gpu_count = cv2.cuda.getCudaEnabledDeviceCount()
        console.print(f"  GPU: [green]可用 ({gpu_count} 设备)[/green]")
    except Exception:
        console.print(f"  GPU: [yellow]不可用[/yellow]")

    # 检测器信息
    detectors = DetectorRegistry.list_detectors()
    console.print(f"\n  已加载检测器: [green]{len(detectors)}[/green]")

    for d in detectors:
        console.print(f"    - {d['display_name']} ({d['name']})")

    console.print()


@cli.command()
@click.argument("detector_name", required=False)
def detectors(detector_name: str = None):
    """列出检测器信息"""
    # 导入检测器
    import core.detectors  # noqa
    from core import DetectorRegistry
    from rich.table import Table

    if detector_name:
        # 显示单个检测器详情
        info = DetectorRegistry.get_detector_info(detector_name)
        if info is None:
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
        # 列出所有检测器
        detector_list = DetectorRegistry.list_detectors()

        table = Table(title="已注册的检测器")
        table.add_column("名称", style="cyan")
        table.add_column("显示名", style="green")
        table.add_column("优先级")
        table.add_column("支持级别")
        table.add_column("版本")

        for d in detector_list:
            table.add_row(
                d["name"],
                d["display_name"],
                str(d["priority"]),
                ", ".join(d["supported_levels"]),
                d["version"],
            )

        console.print(table)


if __name__ == "__main__":
    cli()

