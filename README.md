# OriginX - 图像/视频质量诊断系统

<p align="center">
  <strong>🔍 企业级图像/视频质量诊断解决方案</strong>
</p>

<p align="center">
  <a href="#特性">特性</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#使用方法">使用方法</a> •
  <a href="#api文档">API文档</a> •
  <a href="#配置说明">配置说明</a>
</p>

---

## 特性

- 🚀 **高性能**: 单图处理 < 50ms，支持 20+ fps 吞吐
- 🎯 **多指标检测**: 图像8项 + 视频3项，共11种质量指标
- 🎬 **视频检测**: 支持视频文件检测（画面冻结、场景变换、视频抖动）
- 🔌 **插件化架构**: 易于扩展新的检测器
- ⚙️ **灵活配置**: 预设模板 + 自定义阈值
- 📊 **可解释结果**: 提供问题原因分析和建议措施
- 🖥️ **多接入方式**: REST API、CLI、Python SDK、Web UI
- ⏰ **定时任务**: 支持 Cron 表达式，自动巡检
- 📄 **多格式报告**: JSON、HTML、Excel、PDF 报告导出

## 检测能力

### 图像检测（8项）

| 检测项 | 说明 | 检测方法 |
|-------|------|---------|
| 模糊检测 | 图像清晰度评估 | Laplacian方差、Sobel梯度、Brenner梯度 |
| 亮度检测 | 过亮/过暗检测 | 直方图分析、亮度统计 |
| 对比度检测 | 低对比度检测 | 标准差、动态范围 |
| 颜色检测 | 偏色/黑白/蓝屏检测 | RGB通道分析、HSV色彩空间 |
| 噪声检测 | 高斯/椒盐/雪花噪声 | 拉普拉斯估计、中值滤波残差 |
| 条纹检测 | 水平/垂直条纹干扰 | FFT频域分析 |
| 遮挡检测 | 镜头遮挡检测 | 纹理分析、区域检测 |
| 信号丢失 | 黑屏/白屏/无信号 | 亮度统计、颜色分析 |

### 视频检测（3项）✨ V1.5 新增

| 检测项 | 说明 | 检测方法 |
|-------|------|---------|
| 画面冻结检测 | 视频画面卡顿、冻结 | 帧间差分、SSIM相似度 |
| 场景变换检测 | 场景切换检测 | 直方图差异、边缘变化 |
| 视频抖动检测 | 画面抖动、不稳定 | 光流法、特征点跟踪 |

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/xxx/originx.git
cd originx

# 安装依赖
pip install -r requirements.txt
pip install -e .
```

### Docker 安装

#### 仅后端服务

```bash
# 构建镜像
docker build -t originx:latest .

# 运行容器
docker run -p 8080:8080 originx:latest
```

#### 完整部署（后端 + 前端）

使用 Docker Compose 一键部署前后端：

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f originx
docker-compose logs -f originx-web

# 停止服务
docker-compose down
```

访问地址：
- 前端 Web UI：http://localhost（默认端口 80）
- 后端 API：http://localhost:8080
- API 文档：http://localhost:8080/docs

> **注意**：完整部署需要配置 `Dockerfile.web` 和更新 `docker-compose.yml`，详见 [Web UI 部署说明](#web-uiv15-新增)

### 验证安装

```bash
# 查看版本和系统信息
originx info

# 查看检测器列表
originx detectors
```

## 使用方法

### CLI 命令行

```bash
# 单图诊断
originx detect image ./test.jpg

# 指定配置模板和检测级别
originx detect image ./test.jpg -p strict -l deep

# 批量诊断
originx detect batch ./images/ -r -o ./results/ --report

# 视频诊断（V1.5 新增）
originx video detect ./test.mp4

# 批量视频诊断
originx video batch ./videos/ --pattern "*.mp4"

# 定时任务管理（V1.5 新增）
originx task create -n "每日巡检" -t batch -c "0 2 * * *" -i /data/images
originx task list
originx task enable <task_id>
originx task disable <task_id>

# 报告导出（V1.5 新增）
originx report export result.json -f excel -f pdf -f html

# 输出JSON格式
originx detect image ./test.jpg -f json -o result.json
```

### API 服务

```bash
# 启动服务
originx serve -p 8080

# 或使用Docker Compose
docker-compose up -d
```

API 调用示例:

```bash
# 文件上传方式
curl -X POST http://localhost:8080/api/v1/diagnose/image \
  -F "file=@test.jpg" \
  -F "profile=normal" \
  -F "level=standard"

# JSON方式
curl -X POST http://localhost:8080/api/v1/diagnose/image/json \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "http://example.com/test.jpg",
    "profile": "normal",
    "level": "standard"
  }'
```

### Python SDK

```python
from services import DiagnosisService
import cv2

# 创建服务实例
service = DiagnosisService()

# 诊断图像
image = cv2.imread("test.jpg")
result = service.diagnose_image(image, level="standard")

# 查看结果
print(f"是否异常: {result.is_abnormal}")
print(f"主要问题: {result.primary_issue}")
print(f"严重程度: {result.severity.value}")

# 获取详细信息
for det in result.detection_results:
    if det.is_abnormal:
        print(f"\n{det.detector_name}:")
        print(f"  说明: {det.explanation}")
        print(f"  原因: {det.possible_causes}")
        print(f"  建议: {det.suggestions}")
```

## API 文档

启动服务后访问:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

### 主要接口

#### 图像诊断
| 接口 | 方法 | 说明 |
|-----|------|-----|
| `/api/v1/diagnose/image` | POST | 单图诊断 |
| `/api/v1/diagnose/batch` | POST | 批量诊断 |

#### 视频诊断（V1.5 新增）
| 接口 | 方法 | 说明 |
|-----|------|-----|
| `/api/v1/video/diagnose` | POST | 视频文件诊断 |
| `/api/v1/video/diagnose/batch` | POST | 批量视频诊断 |
| `/api/v1/video/detectors` | GET | 视频检测器列表 |

#### 任务管理（V1.5 新增）
| 接口 | 方法 | 说明 |
|-----|------|-----|
| `/api/v1/tasks` | GET | 获取任务列表 |
| `/api/v1/tasks` | POST | 创建定时任务 |
| `/api/v1/tasks/{task_id}` | GET | 获取任务详情 |
| `/api/v1/tasks/{task_id}` | PUT | 更新任务 |
| `/api/v1/tasks/{task_id}` | DELETE | 删除任务 |
| `/api/v1/tasks/{task_id}/enable` | POST | 启用任务 |
| `/api/v1/tasks/{task_id}/disable` | POST | 禁用任务 |
| `/api/v1/tasks/{task_id}/executions` | GET | 获取执行历史 |

#### 系统管理
| 接口 | 方法 | 说明 |
|-----|------|-----|
| `/api/v1/config` | GET/PUT | 配置管理 |
| `/api/v1/config/profiles` | GET | 获取配置模板 |
| `/api/v1/detectors` | GET | 检测器列表 |
| `/api/v1/health` | GET | 健康检查 |

## 配置说明

### 配置模板

| 模板 | 说明 | 适用场景 |
|-----|------|---------|
| `strict` | 严格模式 | 金融、银行等高要求场景 |
| `normal` | 标准模式 | 园区、企业等一般场景 |
| `loose` | 宽松模式 | 户外、复杂环境 |

### 检测级别

| 级别 | 说明 | 耗时 |
|-----|------|-----|
| `fast` | 快速筛查 | < 5ms |
| `standard` | 标准检测 | < 20ms |
| `deep` | 深度分析 | < 100ms |

### 配置文件示例

```yaml
# config.yaml
profile: normal
detection_level: standard
parallel_detection: true
max_workers: 4

# 自定义阈值
custom_thresholds:
  blur_threshold: 120
  brightness_min: 25

# 服务器配置
server:
  host: 0.0.0.0
  port: 8080
  workers: 4
```

## Web UI（V1.5 新增）

### 开发环境部署

```bash
# 1. 启动后端 API 服务
originx serve -p 8080

# 2. 进入前端目录
cd web

# 3. 安装依赖
npm install

# 4. 启动开发服务器（默认端口 3000）
npm run dev
```

访问地址：http://localhost:3000

开发环境会自动代理 API 请求到后端（配置在 `vite.config.ts` 中）。

### 生产环境部署

#### 方式一：构建静态文件 + Nginx

```bash
# 1. 构建前端项目
cd web
npm install
npm run build

# 2. 构建产物在 web/dist 目录
# 3. 配置 Nginx
```

**Nginx 配置示例**：

```nginx
server {
    listen 80;
    server_name originx.example.com;
    
    # 前端静态文件
    location / {
        root /path/to/originx/web/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }
    
    # 后端 API 代理
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 方式二：Docker 部署（推荐）

创建 `Dockerfile.web`：

```dockerfile
# 构建阶段
FROM node:18-alpine AS builder
WORKDIR /app
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# 运行阶段
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

创建 `web/nginx.conf`：

```nginx
server {
    listen 80;
    server_name localhost;
    
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://originx:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

更新 `docker-compose.yml`：

```yaml
services:
  originx:
    # ... 后端配置 ...
  
  originx-web:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: originx-web
    ports:
      - "80:80"
    depends_on:
      - originx
    restart: unless-stopped
```

启动服务：

```bash
docker-compose up -d
```

#### 方式三：集成到后端服务

将构建后的静态文件复制到后端服务目录，由 FastAPI 直接提供静态文件服务：

```python
# 在 api/main.py 中添加
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="web/dist", html=True), name="static")
```

然后构建前端并复制文件：

```bash
cd web && npm run build
cp -r dist/* ../static/
```

### 环境配置

#### 开发环境

开发环境使用 Vite 代理，配置在 `vite.config.ts` 中：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',  // 后端 API 地址
      changeOrigin: true,
    },
  },
}
```

#### 生产环境

生产环境需要配置 API 基础地址，有两种方式：

**方式一：使用环境变量**

创建 `web/.env.production`：

```env
VITE_API_BASE_URL=http://your-api-server:8080
```

修改 `web/src/api/request.ts`：

```typescript
const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 60000,
})
```

**方式二：使用 Nginx 代理（推荐）**

前端请求统一使用相对路径 `/api`，由 Nginx 代理到后端，无需修改代码。这是生产环境推荐的方式，配置简单且性能好。

### 常见问题

#### 前端无法连接后端 API

1. **检查后端服务是否启动**：
   ```bash
   curl http://localhost:8080/api/v1/health
   ```

2. **检查 CORS 配置**：
   确保后端 API 允许前端域名访问，在 `api/main.py` 中配置：
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000", "http://localhost"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **检查代理配置**：
   - 开发环境：检查 `vite.config.ts` 中的代理配置
   - 生产环境：检查 Nginx 配置中的 `/api` 代理规则

#### 构建失败

```bash
# 清除缓存重新安装
cd web
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### 静态资源加载失败

确保构建后的 `dist` 目录包含所有资源文件，检查 `vite.config.ts` 中的 `base` 配置：

```typescript
export default defineConfig({
  base: '/',  // 如果部署在子路径，改为 '/originx/'
  // ...
})
```

### Web UI 功能

- 📊 **仪表盘**: 系统概览、健康度统计、异常趋势图表
- 🔍 **检测中心**: 图像/视频上传检测、结果查看、批量检测
- ⏰ **任务管理**: 定时任务配置、执行历史、任务控制
- ⚙️ **系统设置**: 阈值配置、检测器管理、配置模板切换

## 项目结构

```
originx/
├── core/                   # 核心算法模块
│   ├── base.py            # 基类定义
│   ├── registry.py        # 检测器注册表
│   ├── pipeline.py        # 图像检测流水线
│   ├── video_pipeline.py  # 视频检测流水线（V1.5）
│   └── detectors/         # 检测器实现
│       ├── video/         # 视频检测器（V1.5）
│       └── ...
├── api/                    # API服务模块
│   ├── main.py            # FastAPI入口
│   ├── routes/            # 路由定义
│   │   ├── video.py      # 视频诊断路由（V1.5）
│   │   └── tasks.py      # 任务管理路由（V1.5）
│   └── schemas/           # 数据模型
├── cli/                    # CLI模块
│   ├── main.py            # CLI入口
│   └── commands/          # 命令实现
│       ├── video.py      # 视频命令（V1.5）
│       └── task.py       # 任务命令（V1.5）
├── scheduler/              # 定时任务模块（V1.5）
│   ├── scheduler.py      # 调度服务
│   └── jobs/             # 任务执行器
├── reports/                # 报告生成模块（V1.5）
│   ├── json_reporter.py
│   ├── html_reporter.py
│   ├── excel_reporter.py
│   └── pdf_reporter.py
├── web/                    # Web UI（V1.5）
│   └── src/              # Vue3 前端代码
├── config/                 # 配置模块
├── services/              # 业务服务层
└── utils/                 # 工具模块
```

## 性能基准

在标准硬件配置下（Intel i7, 16GB RAM）:

| 检测级别 | 1080P图像 | 4K图像 |
|---------|----------|--------|
| fast | ~5ms | ~15ms |
| standard | ~20ms | ~50ms |
| deep | ~60ms | ~150ms |

运行基准测试:

```bash
originx benchmark -n 1000
```

## 开发指南

```bash
# 安装开发依赖
make dev

# 运行测试
make test

# 代码格式化
make format

# 代码检查
make lint
```

## 许可证

MIT License

## 版本历史

详见 [CHANGELOG.md](./CHANGELOG.md)

## 文档

- 📖 [用户指南](./doc/用户指南.md) - 详细使用教程
- 📚 [API 文档](./doc/API文档.md) - 完整 API 接口说明
- 🏗️ [系统设计](./doc/04-单机版系统设计.md) - 架构设计文档
- 🗺️ [发展规划](./doc/05-后续发展规划.md) - 产品路线图
- 🔧 [技术栈演进](./doc/07-技术栈演进规划.md) - 技术选型规划

## 贡献

欢迎提交 Issue 和 Pull Request！

