# -*- coding: utf-8 -*-
"""
任务管理 CLI 命令
"""

import click
from rich.console import Console
from rich.table import Table

from scheduler import SchedulerService, TaskType

console = Console()


@click.group(name="task")
def task_group():
    """任务管理命令组"""
    pass


@task_group.command(name="list")
def list_tasks():
    """列出所有任务"""
    scheduler = SchedulerService()
    tasks = scheduler.get_all_tasks()
    
    if not tasks:
        console.print("[yellow]暂无任务[/yellow]")
        return
    
    table = Table(title="定时任务列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("类型")
    table.add_column("Cron")
    table.add_column("状态")
    table.add_column("下次执行")
    
    for task in tasks:
        status = "[green]启用[/green]" if task.enabled else "[dim]禁用[/dim]"
        next_run = task.next_run_at.strftime("%Y-%m-%d %H:%M") if task.next_run_at else "-"
        
        table.add_row(
            task.id,
            task.name,
            task.task_type.value,
            task.cron_expression,
            status,
            next_run,
        )
    
    console.print(table)


@task_group.command(name="create")
@click.option("--name", "-n", required=True, help="任务名称")
@click.option("--type", "-t", "task_type", default="batch",
              type=click.Choice(["batch", "sample", "video"]),
              help="任务类型")
@click.option("--cron", "-c", required=True, help="Cron表达式")
@click.option("--input", "-i", "input_path", required=True, help="输入路径")
@click.option("--pattern", "-p", default="*.jpg", help="文件匹配模式")
@click.option("--output", "-o", default="./reports", help="输出路径")
@click.option("--profile", default="normal", help="配置模板")
@click.option("--disabled", is_flag=True, help="创建后不启用")
def create_task(
    name: str,
    task_type: str,
    cron: str,
    input_path: str,
    pattern: str,
    output: str,
    profile: str,
    disabled: bool,
):
    """创建新任务"""
    scheduler = SchedulerService()
    
    task = scheduler.create_task(
        name=name,
        task_type=TaskType(task_type),
        cron_expression=cron,
        enabled=not disabled,
        config={
            "input_path": input_path,
            "pattern": pattern,
            "profile": profile,
            "recursive": True,
        },
        output={
            "path": output,
            "format": ["json"],
        },
    )
    
    console.print(f"[green]✓ 任务创建成功[/green]")
    console.print(f"  ID: {task.id}")
    console.print(f"  名称: {task.name}")
    console.print(f"  类型: {task.task_type.value}")
    console.print(f"  Cron: {task.cron_expression}")


@task_group.command(name="delete")
@click.argument("task_id")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
def delete_task(task_id: str, yes: bool):
    """删除任务"""
    scheduler = SchedulerService()
    
    task = scheduler.get_task(task_id)
    if not task:
        console.print(f"[red]任务不存在: {task_id}[/red]")
        return
    
    if not yes:
        if not click.confirm(f"确定要删除任务 '{task.name}' 吗？"):
            return
    
    scheduler.delete_task(task_id)
    console.print(f"[green]✓ 任务已删除[/green]")


@task_group.command(name="enable")
@click.argument("task_id")
def enable_task(task_id: str):
    """启用任务"""
    scheduler = SchedulerService()
    
    if scheduler.enable_task(task_id):
        console.print(f"[green]✓ 任务已启用[/green]")
    else:
        console.print(f"[red]任务不存在: {task_id}[/red]")


@task_group.command(name="disable")
@click.argument("task_id")
def disable_task(task_id: str):
    """禁用任务"""
    scheduler = SchedulerService()
    
    if scheduler.disable_task(task_id):
        console.print(f"[green]✓ 任务已禁用[/green]")
    else:
        console.print(f"[red]任务不存在: {task_id}[/red]")


@task_group.command(name="run")
@click.argument("task_id")
def run_task(task_id: str):
    """立即执行任务"""
    scheduler = SchedulerService()
    
    task = scheduler.get_task(task_id)
    if not task:
        console.print(f"[red]任务不存在: {task_id}[/red]")
        return
    
    console.print(f"[yellow]正在执行任务: {task.name}...[/yellow]")
    scheduler.run_task_now(task_id)
    console.print(f"[green]✓ 任务已开始执行[/green]")


@task_group.command(name="history")
@click.option("--task", "-t", "task_id", default=None, help="任务ID")
@click.option("--limit", "-l", default=20, help="显示数量")
def show_history(task_id: str, limit: int):
    """查看执行历史"""
    scheduler = SchedulerService()
    executions = scheduler.get_executions(task_id=task_id, limit=limit)
    
    if not executions:
        console.print("[yellow]暂无执行记录[/yellow]")
        return
    
    table = Table(title="执行历史")
    table.add_column("时间")
    table.add_column("任务名称")
    table.add_column("结果")
    table.add_column("检测数")
    table.add_column("异常数")
    table.add_column("耗时")
    
    for execution in executions:
        time_str = execution.started_at.strftime("%Y-%m-%d %H:%M") if execution.started_at else "-"
        status = "[green]成功[/green]" if execution.status.value == "completed" else "[red]失败[/red]"
        duration = f"{execution.duration_seconds:.1f}s" if execution.duration_seconds else "-"
        
        table.add_row(
            time_str,
            execution.task_name,
            status,
            str(execution.total_items),
            str(execution.abnormal_count),
            duration,
        )
    
    console.print(table)

