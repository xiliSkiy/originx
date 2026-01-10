"""FastAPI应用入口"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from config import AppConfig, get_config, set_config
from .routes import diagnose, config as config_routes, detectors, system, video, tasks, stream, baseline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """应用生命周期管理"""
    # 启动时
    print("OriginX API Server starting...")

    # 加载配置
    app_config = AppConfig.load()
    set_config(app_config)

    # 导入检测器以触发注册
    import core.detectors  # noqa

    print(f"Loaded {len(core.DetectorRegistry.list_detectors())} detectors")
    print("OriginX API Server started successfully")

    yield

    # 关闭时
    print("OriginX API Server shutting down...")


def create_app(config: AppConfig = None) -> FastAPI:
    """
    创建FastAPI应用实例

    Args:
        config: 应用配置

    Returns:
        FastAPI: 应用实例
    """
    if config:
        set_config(config)

    app = FastAPI(
        title="OriginX",
        description="图像/视频质量诊断系统 API",
        version="1.5.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 请求日志中间件
    class RequestLoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable):
            start_time = time.time()
            # 记录请求信息
            logger.info(f"收到请求: {request.method} {request.url.path}")
            logger.info(f"  查询参数: {dict(request.query_params)}")
            logger.info(f"  客户端: {request.client.host if request.client else 'unknown'}")
            
            try:
                response = await call_next(request)
                process_time = time.time() - start_time
                logger.info(f"请求完成: {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
                return response
            except Exception as e:
                process_time = time.time() - start_time
                logger.error(f"请求失败: {request.method} {request.url.path} - 错误: {e} ({process_time:.3f}s)", exc_info=True)
                raise
    
    app.add_middleware(RequestLoggingMiddleware)
    
    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(
        diagnose.router,
        prefix="/api/v1/diagnose",
        tags=["诊断"],
    )
    app.include_router(
        config_routes.router,
        prefix="/api/v1/config",
        tags=["配置"],
    )
    app.include_router(
        detectors.router,
        prefix="/api/v1/detectors",
        tags=["检测器"],
    )
    app.include_router(
        system.router,
        prefix="/api/v1",
        tags=["系统"],
    )
    app.include_router(
        video.router,
        prefix="/api/v1",
        tags=["视频诊断"],
    )
    app.include_router(
        tasks.router,
        prefix="/api/v1",
        tags=["任务管理"],
    )
    app.include_router(
        stream.router,
        prefix="/api/v1/diagnose",
        tags=["流检测"],
    )
    app.include_router(
        baseline.router,
        prefix="/api/v1",
        tags=["基准图像"],
    )

    return app


# 默认应用实例
app = create_app()

