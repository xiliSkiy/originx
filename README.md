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
- 🎯 **多指标检测**: 模糊、亮度、对比度、颜色、噪声、条纹、遮挡、信号丢失
- 🔌 **插件化架构**: 易于扩展新的检测器
- ⚙️ **灵活配置**: 预设模板 + 自定义阈值
- 📊 **可解释结果**: 提供问题原因分析和建议措施
- 🖥️ **多接入方式**: REST API、CLI、Python SDK

## 检测能力

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

```bash
# 构建镜像
docker build -t originx:latest .

# 运行容器
docker run -p 8080:8080 originx:latest
```

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

| 接口 | 方法 | 说明 |
|-----|------|-----|
| `/api/v1/diagnose/image` | POST | 单图诊断 |
| `/api/v1/diagnose/batch` | POST | 批量诊断 |
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

## 项目结构

```
originx/
├── core/                   # 核心算法模块
│   ├── base.py            # 基类定义
│   ├── registry.py        # 检测器注册表
│   ├── pipeline.py        # 检测流水线
│   └── detectors/         # 检测器实现
├── api/                    # API服务模块
│   ├── main.py            # FastAPI入口
│   ├── routes/            # 路由定义
│   └── schemas/           # 数据模型
├── cli/                    # CLI模块
│   ├── main.py            # CLI入口
│   └── commands/          # 命令实现
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

## 贡献

欢迎提交 Issue 和 Pull Request！

