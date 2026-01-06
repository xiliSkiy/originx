# OriginX Makefile
# 常用命令集合

.PHONY: help install dev test lint format clean docker run serve

# 默认目标
help:
	@echo "OriginX - 图像/视频质量诊断系统"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    - 安装项目依赖"
	@echo "  make dev        - 安装开发依赖"
	@echo "  make test       - 运行测试"
	@echo "  make lint       - 代码检查"
	@echo "  make format     - 代码格式化"
	@echo "  make clean      - 清理临时文件"
	@echo "  make docker     - 构建Docker镜像"
	@echo "  make run        - 启动Docker容器"
	@echo "  make serve      - 本地启动服务"
	@echo "  make benchmark  - 运行性能测试"

# 安装依赖
install:
	pip install -r requirements.txt
	pip install -e .

# 安装开发依赖
dev:
	pip install -r requirements-dev.txt
	pip install -e .

# 运行测试
test:
	pytest tests/ -v --cov=core --cov=api --cov=cli

# 代码检查
lint:
	flake8 core/ api/ cli/ config/ services/ utils/
	mypy core/ api/ cli/ --ignore-missing-imports

# 代码格式化
format:
	black core/ api/ cli/ config/ services/ utils/ tests/
	isort core/ api/ cli/ config/ services/ utils/ tests/

# 清理
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/

# 构建Docker镜像
docker:
	docker build -t originx:latest .

# 启动Docker容器
run:
	docker-compose up -d

# 停止Docker容器
stop:
	docker-compose down

# 本地启动服务
serve:
	originx serve --reload

# 性能测试
benchmark:
	originx benchmark -n 100

# 生成配置文件
config:
	originx config init -o config.yaml

# 检查系统信息
info:
	originx info

