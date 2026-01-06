"""日志工具"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import get_config


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    设置日志配置

    Args:
        level: 日志级别
        log_file: 日志文件路径
        max_size: 单个日志文件最大大小
        backup_count: 备份文件数量
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称

    Returns:
        logging.Logger: 日志器实例
    """
    return logging.getLogger(name)


# 初始化日志
def init_logging_from_config() -> None:
    """从配置初始化日志"""
    try:
        config = get_config()
        setup_logging(
            level=config.log.level,
            log_file=config.log.file,
            max_size=config.log.max_size,
            backup_count=config.log.backup_count,
        )
    except Exception:
        # 使用默认配置
        setup_logging()

