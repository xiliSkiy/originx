"""配置命令"""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def config():
    """配置管理命令"""
    pass


@config.command("show")
@click.option("--profile", help="显示指定配置模板")
def show_config(profile: str = None):
    """
    显示配置信息

    示例:
        originx config show
        originx config show --profile strict
    """
    from config import AppConfig, PRESET_PROFILES

    if profile:
        if profile not in PRESET_PROFILES:
            console.print(f"[red]配置模板 '{profile}' 不存在[/red]")
            console.print(f"可用模板: {list(PRESET_PROFILES.keys())}")
            return

        p = PRESET_PROFILES[profile]
        console.print(f"\n[bold]{p.display_name}[/bold] ({p.name})")
        console.print(f"描述: {p.description}\n")

        table = Table(title="阈值配置")
        table.add_column("参数", style="cyan")
        table.add_column("值", style="green")

        thresholds = p.thresholds
        table.add_row("blur_threshold", str(thresholds.blur_threshold))
        table.add_row("brightness_min", str(thresholds.brightness_min))
        table.add_row("brightness_max", str(thresholds.brightness_max))
        table.add_row("contrast_min", str(thresholds.contrast_min))
        table.add_row("saturation_min", str(thresholds.saturation_min))
        table.add_row("color_cast_threshold", str(thresholds.color_cast_threshold))
        table.add_row("noise_threshold", str(thresholds.noise_threshold))
        table.add_row("stripe_threshold", str(thresholds.stripe_threshold))

        console.print(table)
    else:
        config = AppConfig.load()

        console.print("\n[bold]当前配置[/bold]\n")
        console.print(f"  配置模板: [green]{config.profile}[/green]")
        console.print(f"  检测级别: [green]{config.detection_level}[/green]")
        console.print(f"  并行检测: [green]{config.parallel_detection}[/green]")
        console.print(f"  最大工作线程: [green]{config.max_workers}[/green]")
        console.print(f"  GPU加速: [green]{config.gpu_enabled}[/green]")

        if config.custom_thresholds:
            console.print("\n  自定义阈值:")
            for key, value in config.custom_thresholds.items():
                console.print(f"    {key}: {value}")

    console.print()


@config.command("profiles")
def list_profiles():
    """列出所有配置模板"""
    from config import PRESET_PROFILES

    table = Table(title="配置模板")
    table.add_column("名称", style="cyan")
    table.add_column("显示名", style="green")
    table.add_column("描述")

    for name, p in PRESET_PROFILES.items():
        table.add_row(name, p.display_name, p.description)

    console.print(table)


@config.command("init")
@click.option("-o", "--output", default="config.yaml", help="输出文件路径")
def init_config(output: str):
    """
    生成默认配置文件

    示例:
        originx config init
        originx config init -o my_config.yaml
    """
    from config import AppConfig

    config = AppConfig()
    config.save(output)

    console.print(f"[green]配置文件已生成: {output}[/green]")


@config.command("validate")
@click.argument("config_path", type=click.Path(exists=True))
def validate_config(config_path: str):
    """
    验证配置文件

    示例:
        originx config validate config.yaml
    """
    try:
        from config import AppConfig

        config = AppConfig.load(config_path)

        console.print(f"[green]✓ 配置文件有效[/green]")
        console.print(f"  配置模板: {config.profile}")
        console.print(f"  检测级别: {config.detection_level}")

    except Exception as e:
        console.print(f"[red]✗ 配置文件无效: {e}[/red]")

