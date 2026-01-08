# OriginX API 文档

> 完整的 REST API 接口说明文档

## 目录

- [基础信息](#基础信息)
- [认证](#认证)
- [图像诊断](#图像诊断)
- [视频诊断](#视频诊断)
- [任务管理](#任务管理)
- [配置管理](#配置管理)
- [检测器管理](#检测器管理)
- [系统信息](#系统信息)
- [错误码](#错误码)

---

## 基础信息

### 基础 URL

```
http://localhost:8080/api/v1
```

### 交互式文档

启动服务后，可访问以下地址查看交互式 API 文档：

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### 请求格式

- **Content-Type**: `application/json` 或 `multipart/form-data`
- **响应格式**: JSON

### 响应结构

所有 API 响应遵循统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

---

## 认证

> ⚠️ **V1.5 版本暂不支持认证**，后续版本将添加 API Key 或 JWT 认证。

---

## 图像诊断

### 1. 单图诊断

**接口**: `POST /diagnose/image`

**描述**: 对单张图像进行质量诊断

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 否 | 图像文件（multipart/form-data） |
| `image` | String | 否 | Base64 编码的图像数据 |
| `image_url` | String | 否 | 图像 URL 地址 |
| `profile` | String | 否 | 配置模板（strict/normal/loose），默认 `normal` |
| `level` | String | 否 | 检测级别（fast/standard/deep），默认 `standard` |
| `detectors` | String | 否 | 检测器列表（逗号分隔），如 `blur,brightness` |
| `return_evidence` | Boolean | 否 | 是否返回证据数据，默认 `true` |

**注意**: `file`、`image`、`image_url` 三者至少提供一个。

**请求示例**:

```bash
# 方式1: 文件上传
curl -X POST http://localhost:8080/api/v1/diagnose/image \
  -F "file=@test.jpg" \
  -F "profile=normal" \
  -F "level=standard"

# 方式2: Base64
curl -X POST http://localhost:8080/api/v1/diagnose/image \
  -F "image=<base64_string>" \
  -F "profile=normal"

# 方式3: URL
curl -X POST http://localhost:8080/api/v1/diagnose/image \
  -F "image_url=http://example.com/image.jpg" \
  -F "profile=strict"
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "img_20260101_120000_abc12345",
    "is_abnormal": true,
    "primary_issue": "blur",
    "severity": "medium",
    "scores": {
      "blur": 0.85,
      "brightness": 0.12,
      "contrast": 0.45
    },
    "issues": [
      {
        "type": "blur",
        "is_abnormal": true,
        "score": 0.85,
        "threshold": 0.5,
        "confidence": 0.92,
        "severity": "medium",
        "explanation": "图像清晰度较低",
        "possible_causes": ["镜头对焦不准", "相机抖动", "运动模糊"],
        "suggestions": ["检查镜头对焦", "使用三脚架", "提高快门速度"],
        "evidence": { ... }
      }
    ],
    "suppressed_issues": [],
    "image_info": {
      "width": 1920,
      "height": 1080
    }
  }
}
```

### 2. 批量诊断

**接口**: `POST /diagnose/batch`

**描述**: 批量诊断多张图像

**请求体**:

```json
{
  "image_paths": [
    "/path/to/image1.jpg",
    "/path/to/image2.jpg"
  ],
  "profile": "normal",
  "level": "standard",
  "detectors": ["blur", "brightness"],
  "output_path": "/path/to/output",
  "generate_report": true
}
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_paths` | Array[String] | 是 | 图像文件路径列表 |
| `profile` | String | 否 | 配置模板，默认 `normal` |
| `level` | String | 否 | 检测级别，默认 `standard` |
| `detectors` | Array[String] | 否 | 检测器列表 |
| `output_path` | String | 否 | 输出目录路径 |
| `generate_report` | Boolean | 否 | 是否生成报告，默认 `true` |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "batch_20260101_120000_abc12345",
    "total": 10,
    "success": 10,
    "failed": 0,
    "normal_count": 7,
    "abnormal_count": 3,
    "summary": {
      "blur": 2,
      "brightness": 1,
      "contrast": 0
    },
    "results": [ ... ],
    "report_path": "/path/to/report.json"
  }
}
```

---

## 视频诊断

### 1. 视频文件诊断

**接口**: `POST /video/diagnose`

**描述**: 诊断上传的视频文件

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `video` | File | 是 | 视频文件（MP4/AVI/MOV） |
| `profile` | String | 否 | 配置模板，默认 `normal` |
| `detectors` | String | 否 | 检测器列表（逗号分隔），如 `freeze,scene_change` |
| `sample_strategy` | String | 否 | 采样策略（interval/scene_change），默认 `interval` |
| `sample_interval` | Float | 否 | 采样间隔（秒），默认 `1.0` |
| `max_frames` | Integer | 否 | 最大采样帧数，默认 `300` |

**请求示例**:

```bash
curl -X POST http://localhost:8080/api/v1/video/diagnose \
  -F "video=@test.mp4" \
  -F "profile=normal" \
  -F "sample_interval=1.0" \
  -F "max_frames=300"
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "video_path": "test.mp4",
    "video_id": "video_20260101_120000_abc12345",
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "duration": 60.5,
    "frame_count": 1815,
    "sampled_frames": 60,
    "is_abnormal": true,
    "overall_score": 0.75,
    "primary_issue": "freeze",
    "severity": "medium",
    "issues": [
      {
        "issue_type": "freeze",
        "severity": "medium",
        "detected_segments": [
          {
            "start_time": 10.5,
            "end_time": 12.0,
            "frame_start": 315,
            "frame_end": 360
          }
        ],
        "total_duration": 1.5,
        "explanation": "检测到画面冻结"
      }
    ],
    "process_time_ms": 1250.5
  }
}
```

### 2. 批量视频诊断

**接口**: `POST /video/diagnose/batch`

**描述**: 批量诊断多个视频文件

**请求体**:

```json
{
  "video_paths": [
    "/path/to/video1.mp4",
    "/path/to/video2.mp4"
  ],
  "profile": "normal",
  "detectors": ["freeze", "scene_change", "shake"],
  "sample_strategy": "interval",
  "sample_interval": 1.0,
  "max_frames": 300
}
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 5,
    "success": 5,
    "failed": 0,
    "normal_count": 3,
    "abnormal_count": 2,
    "results": [ ... ],
    "process_time_ms": 6250.5
  }
}
```

### 3. 获取视频检测器列表

**接口**: `GET /video/detectors`

**描述**: 获取可用的视频检测器列表

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "name": "freeze",
      "display_name": "画面冻结检测",
      "description": "检测视频画面是否冻结或卡顿",
      "issue_type": "freeze",
      "version": "1.0"
    },
    {
      "name": "scene_change",
      "display_name": "场景变换检测",
      "description": "检测视频场景是否发生切换",
      "issue_type": "scene_change",
      "version": "1.0"
    },
    {
      "name": "shake",
      "display_name": "视频抖动检测",
      "description": "检测视频画面是否抖动",
      "issue_type": "shake",
      "version": "1.0"
    }
  ]
}
```

---

## 任务管理

### 1. 获取任务列表

**接口**: `GET /tasks`

**描述**: 获取所有定时任务列表

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "tasks": [
      {
        "id": "task_001",
        "name": "每日巡检",
        "description": "每天凌晨2点执行批量检测",
        "task_type": "batch",
        "cron_expression": "0 2 * * *",
        "enabled": true,
        "config": {
          "input_path": "/data/images",
          "pattern": "*.jpg"
        },
        "output": {
          "report": true,
          "format": ["json", "html"]
        },
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "last_run_at": "2026-01-01T02:00:00",
        "next_run_at": "2026-01-02T02:00:00"
      }
    ],
    "total": 1
  }
}
```

### 2. 创建任务

**接口**: `POST /tasks`

**描述**: 创建新的定时任务

**请求体**:

```json
{
  "name": "每日巡检",
  "description": "每天凌晨2点执行批量检测",
  "task_type": "batch",
  "cron_expression": "0 2 * * *",
  "enabled": true,
  "config": {
    "input_path": "/data/images",
    "pattern": "*.jpg",
    "profile": "normal",
    "level": "standard"
  },
  "output": {
    "report": true,
    "format": ["json", "html"],
    "path": "/data/reports"
  }
}
```

**任务类型** (`task_type`):

- `batch`: 批量图像检测
- `sample`: 抽样检测
- `video`: 视频检测

**Cron 表达式示例**:

- `0 2 * * *`: 每天凌晨2点
- `0 */6 * * *`: 每6小时
- `0 9,12,18 * * 1-5`: 工作日9点、12点、18点

### 3. 获取任务详情

**接口**: `GET /tasks/{task_id}`

**描述**: 获取指定任务的详细信息

### 4. 更新任务

**接口**: `PUT /tasks/{task_id}`

**描述**: 更新任务配置

**请求体**: 同创建任务，所有字段可选

### 5. 删除任务

**接口**: `DELETE /tasks/{task_id}`

**描述**: 删除指定任务

### 6. 启用/禁用任务

**接口**: 
- `POST /tasks/{task_id}/enable` - 启用任务
- `POST /tasks/{task_id}/disable` - 禁用任务

### 7. 立即执行任务

**接口**: `POST /tasks/{task_id}/run`

**描述**: 立即执行指定任务（不等待定时触发）

### 8. 获取执行历史

**接口**: `GET /tasks/{task_id}/executions`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | Integer | 否 | 返回数量限制（1-200），默认 50 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "executions": [
      {
        "id": "exec_001",
        "task_id": "task_001",
        "task_name": "每日巡检",
        "status": "success",
        "started_at": "2026-01-01T02:00:00",
        "finished_at": "2026-01-01T02:05:30",
        "duration_seconds": 330,
        "total_items": 100,
        "normal_count": 85,
        "abnormal_count": 15,
        "error_count": 0,
        "report_path": "/data/reports/report_20260101_020000.json",
        "error_message": null
      }
    ],
    "total": 1
  }
}
```

### 9. 获取所有执行历史

**接口**: `GET /tasks/executions/all`

**描述**: 获取所有任务的执行历史

**查询参数**: 同获取执行历史

---

## 配置管理

### 1. 获取当前配置

**接口**: `GET /config`

**描述**: 获取当前系统配置

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "profile": "normal",
    "detection_level": "standard",
    "parallel_detection": true,
    "max_workers": 4,
    "thresholds": {
      "blur_threshold": 0.5,
      "brightness_min": 25,
      "brightness_max": 230,
      "contrast_min": 0.3,
      "saturation_min": 0.2,
      "color_cast_threshold": 0.15,
      "noise_threshold": 0.1,
      "stripe_threshold": 0.05
    }
  }
}
```

### 2. 更新配置

**接口**: `PUT /config`

**描述**: 更新系统配置

**请求体**:

```json
{
  "profile": "strict",
  "detection_level": "deep",
  "parallel_detection": true,
  "max_workers": 8
}
```

### 3. 获取配置模板列表

**接口**: `GET /config/profiles`

**描述**: 获取所有可用的配置模板

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "profiles": [
      {
        "name": "strict",
        "display_name": "严格模式",
        "description": "适用于金融、银行等高要求场景",
        "thresholds": { ... }
      },
      {
        "name": "normal",
        "display_name": "标准模式",
        "description": "适用于园区、企业等一般场景",
        "thresholds": { ... }
      },
      {
        "name": "loose",
        "display_name": "宽松模式",
        "description": "适用于户外、复杂环境",
        "thresholds": { ... }
      }
    ]
  }
}
```

### 4. 更新阈值

**接口**: `PUT /config/thresholds`

**描述**: 更新检测阈值

**请求体**:

```json
{
  "blur_threshold": 0.6,
  "brightness_min": 30,
  "brightness_max": 220,
  "contrast_min": 0.35
}
```

---

## 检测器管理

### 1. 获取检测器列表

**接口**: `GET /detectors`

**描述**: 获取所有可用的图像检测器列表

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "name": "blur",
      "display_name": "模糊检测",
      "description": "检测图像清晰度",
      "issue_type": "blur",
      "supported_levels": ["fast", "standard", "deep"],
      "version": "1.0",
      "priority": 5
    },
    {
      "name": "brightness",
      "display_name": "亮度检测",
      "description": "检测图像过亮或过暗",
      "issue_type": "brightness",
      "supported_levels": ["fast", "standard", "deep"],
      "version": "1.0",
      "priority": 5
    }
  ]
}
```

### 2. 获取检测器详情

**接口**: `GET /detectors/{detector_name}`

**描述**: 获取指定检测器的详细信息

---

## 系统信息

### 1. 健康检查

**接口**: `GET /health`

**描述**: 检查系统健康状态

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "healthy",
    "version": "1.5.0",
    "uptime": 3600,
    "timestamp": "2026-01-01T12:00:00"
  }
}
```

### 2. 系统信息

**接口**: `GET /system/info`

**描述**: 获取系统详细信息

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "version": "1.5.0",
    "python_version": "3.9.0",
    "opencv_version": "4.8.0",
    "platform": "Linux",
    "cpu_count": 8,
    "memory_total_gb": 16.0,
    "detectors_count": 11,
    "image_detectors": 8,
    "video_detectors": 3
  }
}
```

---

## 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 请求参数错误 |
| 404 | 404 | 资源不存在 |
| 500 | 500 | 服务器内部错误 |

**错误响应格式**:

```json
{
  "code": 400,
  "message": "请求参数错误",
  "detail": "图像文件不能为空"
}
```

---

## 使用示例

### Python 示例

```python
import requests

# 单图诊断
files = {'file': open('test.jpg', 'rb')}
data = {
    'profile': 'normal',
    'level': 'standard'
}
response = requests.post(
    'http://localhost:8080/api/v1/diagnose/image',
    files=files,
    data=data
)
result = response.json()
print(result)

# 视频诊断
files = {'video': open('test.mp4', 'rb')}
data = {
    'profile': 'normal',
    'sample_interval': 1.0
}
response = requests.post(
    'http://localhost:8080/api/v1/video/diagnose',
    files=files,
    data=data
)
result = response.json()
print(result)

# 创建定时任务
task_data = {
    'name': '每日巡检',
    'task_type': 'batch',
    'cron_expression': '0 2 * * *',
    'enabled': True,
    'config': {
        'input_path': '/data/images',
        'pattern': '*.jpg'
    }
}
response = requests.post(
    'http://localhost:8080/api/v1/tasks',
    json=task_data
)
result = response.json()
print(result)
```

### JavaScript 示例

```javascript
// 单图诊断
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('profile', 'normal');
formData.append('level', 'standard');

fetch('http://localhost:8080/api/v1/diagnose/image', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));

// 创建定时任务
fetch('http://localhost:8080/api/v1/tasks', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: '每日巡检',
    task_type: 'batch',
    cron_expression: '0 2 * * *',
    enabled: true,
    config: {
      input_path: '/data/images',
      pattern: '*.jpg'
    }
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## 注意事项

1. **文件大小限制**: 默认最大文件大小为 100MB，可通过配置调整
2. **并发限制**: 建议单机并发请求不超过 100
3. **超时设置**: 视频诊断可能耗时较长，建议设置合理的超时时间
4. **临时文件**: 上传的文件会临时保存，处理完成后自动清理
5. **Cron 表达式**: 使用标准 Cron 格式，最小粒度 1 分钟

---

*最后更新: 2026-01-XX*
