# 更新日志

本文档记录 OriginX 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.5.0] - 2026-01-XX

### 🎉 新增功能

#### 视频检测能力
- ✨ 支持视频文件检测（MP4/AVI/MOV 格式）
- ✨ 画面冻结检测器（FreezeDetector）
- ✨ 场景变换检测器（SceneChangeDetector）
- ✨ 视频抖动检测器（ShakeDetector）
- ✨ 视频处理框架（VideoLoader、FrameSampler、FrameBuffer）
- ✨ 视频诊断流水线（VideoDiagnosisPipeline）

#### Web 管理界面
- ✨ Vue3 + Element Plus 前端框架
- ✨ 仪表盘页面（Dashboard）- 系统概览、健康度统计
- ✨ 检测中心页面（Detection）- 图像/视频上传检测、结果查看
- ✨ 任务管理页面（Tasks）- 定时任务配置、执行历史
- ✨ 系统设置页面（Settings）- 阈值配置、检测器管理

#### 定时任务系统
- ✨ APScheduler 集成，支持 Cron 表达式
- ✨ 任务类型：批量检测、抽样检测、视频检测
- ✨ 任务管理 API（创建、更新、删除、启用/禁用）
- ✨ 任务执行历史记录
- ✨ CLI 任务管理命令

#### 报告导出增强
- ✨ Excel 报告导出（openpyxl）
- ✨ PDF 报告导出（reportlab）
- ✨ HTML 报告模板优化（Jinja2）
- ✨ 多格式报告生成服务

### 🔧 改进

- ⚡ 优化视频处理性能
- 📝 完善 API 文档和错误信息
- 🎨 改进前端用户体验
- 🔍 增强检测结果可解释性

### 📚 文档

- 📖 新增用户指南文档
- 📚 完善 API 接口文档
- 📝 更新 README.md，添加 V1.5 新功能说明
- 📋 创建 CHANGELOG.md

### 🐛 修复

- 修复批量诊断中部分检测器未执行的问题
- 修复视频检测中的内存泄漏问题
- 修复定时任务执行异常时的错误处理

---

## [1.0.0] - 2025-XX-XX

### 🎉 初始版本

#### 核心功能
- ✨ 8种图像质量检测器
  - 模糊检测（BlurDetector）
  - 亮度检测（BrightnessDetector）
  - 对比度检测（ContrastDetector）
  - 颜色检测（ColorDetector）
  - 噪声检测（NoiseDetector）
  - 条纹检测（StripeDetector）
  - 遮挡检测（OcclusionDetector）
  - 信号丢失检测（SignalLossDetector）

#### 接入方式
- ✨ REST API（FastAPI）
- ✨ CLI 命令行工具（Click）
- ✨ Python SDK

#### 配置管理
- ✨ 多配置模板（strict/normal/loose）
- ✨ 三级检测级别（fast/standard/deep）
- ✨ 自定义阈值配置

#### 输出能力
- ✨ JSON 格式结果
- ✨ 批量诊断报告
- ✨ HTML 可视化展示

#### 工程能力
- ✨ Docker 容器化
- ✨ 单元测试框架
- ✨ 代码质量工具（Black、isort、mypy）

---

## 版本说明

- **主版本号（Major）**: 不兼容的 API 修改
- **次版本号（Minor）**: 向下兼容的功能性新增
- **修订号（Patch）**: 向下兼容的问题修正

## 变更类型

- `新增`: 新功能
- `改进`: 对现有功能的改进
- `修复`: 问题修复
- `文档`: 文档相关变更
- `性能`: 性能优化
- `重构`: 代码重构
- `移除`: 功能移除

---

*更多详细信息请参考 [GitHub Releases](https://github.com/xxx/originx/releases)*
