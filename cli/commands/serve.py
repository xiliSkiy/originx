"""服务命令"""

import click
from rich.console import Console

console = Console()


@click.command()
@click.option("--host", default="0.0.0.0", help="监听地址")
@click.option("-p", "--port", default=8080, type=int, help="监听端口")
@click.option("-w", "--workers", default=4, type=int, help="工作进程数")
@click.option("-c", "--config", "config_path", type=click.Path(), help="配置文件路径")
@click.option("--reload", is_flag=True, help="开发模式，自动重载")
def serve(host: str, port: int, workers: int, config_path: str, reload: bool):
    """
    启动API服务

    示例:
        originx serve
        originx serve -p 8080 -w 4
        originx serve -c config.yaml --reload
    """
    import os
    import uvicorn

    # 设置配置文件环境变量
    if config_path:
        os.environ["ORIGINX_CONFIG"] = config_path

    console.print()
    console.print("[bold blue]OriginX API Server[/bold blue]")
    console.print(f"  地址: http://{host}:{port}")
    console.print(f"  文档: http://{host}:{port}/docs")
    console.print(f"  工作进程: {workers}")
    if config_path:
        console.print(f"  配置文件: {config_path}")
    console.print()

    # 启动服务
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        workers=1 if reload else workers,
        reload=reload,
        log_level="info",
    )

