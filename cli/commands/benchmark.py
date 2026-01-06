"""基准测试命令"""

import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

console = Console()


@click.command()
@click.option("--images", type=click.Path(exists=True), help="测试图片目录")
@click.option("-n", "--count", default=100, type=int, help="测试次数")
@click.option("-l", "--level", default="standard", help="检测级别")
@click.option("--warmup", default=10, type=int, help="预热次数")
def benchmark(
    images: Optional[str],
    count: int,
    level: str,
    warmup: int,
):
    """
    性能基准测试

    示例:
        originx benchmark
        originx benchmark --images ./test_images/ -n 1000
    """
    import cv2
    import numpy as np

    # 导入模块
    import core.detectors  # noqa
    from core import DiagnosisPipeline, DetectorRegistry, DetectionLevel
    from config import AppConfig

    console.print("\n[bold blue]OriginX 性能基准测试[/bold blue]\n")

    # 准备测试图像
    test_images = []

    if images:
        image_dir = Path(images)
        for pattern in ["*.jpg", "*.png", "*.jpeg"]:
            test_images.extend(list(image_dir.glob(pattern)))

        if test_images:
            test_images = [cv2.imread(str(p)) for p in test_images[:20]]
            test_images = [img for img in test_images if img is not None]

    if not test_images:
        # 生成测试图像
        console.print("生成测试图像...")
        for _ in range(10):
            # 生成随机图像
            img = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
            test_images.append(img)

    console.print(f"测试图像数量: {len(test_images)}")
    console.print(f"测试次数: {count}")
    console.print(f"检测级别: {level}")

    # 准备流水线
    config = AppConfig()
    threshold_config = config.get_threshold_dict()
    threshold_config["parallel_detection"] = True
    threshold_config["max_workers"] = 4

    pipeline = DiagnosisPipeline(threshold_config)
    detection_level = DetectionLevel.from_string(level)

    # 预热
    console.print(f"\n预热中 ({warmup} 次)...")
    for i in range(warmup):
        img = test_images[i % len(test_images)]
        pipeline.diagnose(img, detection_level)

    # 基准测试
    console.print("\n运行基准测试...")

    times = []
    with Progress(console=console) as progress:
        task = progress.add_task("测试中...", total=count)

        for i in range(count):
            img = test_images[i % len(test_images)]

            start = time.perf_counter()
            result = pipeline.diagnose(img, detection_level)
            elapsed = (time.perf_counter() - start) * 1000

            times.append(elapsed)
            progress.advance(task)

    # 统计结果
    times_array = np.array(times)

    results = {
        "平均耗时": f"{np.mean(times_array):.2f} ms",
        "中位数": f"{np.median(times_array):.2f} ms",
        "最小值": f"{np.min(times_array):.2f} ms",
        "最大值": f"{np.max(times_array):.2f} ms",
        "标准差": f"{np.std(times_array):.2f} ms",
        "P95": f"{np.percentile(times_array, 95):.2f} ms",
        "P99": f"{np.percentile(times_array, 99):.2f} ms",
        "吞吐量": f"{1000 / np.mean(times_array):.1f} fps",
    }

    # 显示结果
    console.print()
    table = Table(title="基准测试结果")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")

    for key, value in results.items():
        table.add_row(key, value)

    console.print(table)

    # 各检测器耗时
    console.print("\n[bold]检测器耗时分布:[/bold]")

    # 单次运行获取详细耗时
    img = test_images[0]
    result = pipeline.diagnose(img, detection_level)

    for det_result in result.detection_results:
        console.print(f"  {det_result.detector_name}: {det_result.process_time_ms:.2f} ms")

    console.print()

