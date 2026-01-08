<template>
  <div class="detection">
    <div class="page-header">
      <h1>检测中心</h1>
      <p>上传图像或视频进行质量诊断</p>
    </div>
    
    <!-- 检测类型选择 -->
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="单图检测" name="single">
        <div class="detection-content">
          <!-- 上传区域 -->
          <div class="upload-section">
            <el-upload
              ref="uploadRef"
              class="upload-area"
              drag
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              @change="handleImageChange"
            >
              <template v-if="!currentImage">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">
                  拖拽图像到此处，或 <em>点击上传</em>
                </div>
                <div class="upload-tip">支持 JPG、PNG、BMP 格式</div>
              </template>
              <template v-else>
                <img :src="imagePreview" class="preview-image" />
              </template>
            </el-upload>
            
            <div class="upload-options" v-if="currentImage">
              <el-form label-width="80px" size="small">
                <el-form-item label="配置模板">
                  <el-select v-model="detectOptions.profile">
                    <el-option label="严格模式" value="strict" />
                    <el-option label="标准模式" value="normal" />
                    <el-option label="宽松模式" value="loose" />
                  </el-select>
                </el-form-item>
                <el-form-item label="检测级别">
                  <el-select v-model="detectOptions.level">
                    <el-option label="快速检测" value="fast" />
                    <el-option label="标准检测" value="standard" />
                    <el-option label="深度检测" value="deep" />
                  </el-select>
                </el-form-item>
              </el-form>
              
              <div class="action-buttons">
                <el-button @click="clearImage">清除</el-button>
                <el-button type="primary" :loading="loading" @click="startDetection">
                  开始检测
                </el-button>
              </div>
            </div>
          </div>
          
          <!-- 检测结果 -->
          <div class="result-section" v-if="imageResult">
            <div class="result-header">
              <h3>检测结果</h3>
              <span :class="['status-tag', imageResult.is_abnormal ? 'abnormal' : 'normal']">
                {{ imageResult.is_abnormal ? '⚠️ 检测到异常' : '✅ 正常' }}
              </span>
            </div>
            
            <div class="result-summary" v-if="imageResult.is_abnormal">
              <div class="summary-item">
                <span class="label">主要问题:</span>
                <span class="value">{{ getIssueTypeName(imageResult.primary_issue) }}</span>
              </div>
              <div class="summary-item">
                <span class="label">严重程度:</span>
                <el-tag :type="getSeverityType(imageResult.severity)" size="small">
                  {{ getSeverityName(imageResult.severity) }}
                </el-tag>
              </div>
            </div>
            
            <div class="result-detectors">
              <h4>检测指标详情</h4>
              <div class="detector-grid">
                <div 
                  v-for="det in imageResult.detection_results" 
                  :key="det.detector_name"
                  :class="['detector-card', { abnormal: det.is_abnormal }]"
                >
                  <div class="detector-icon">{{ getDetectorIcon(det.detector_name) }}</div>
                  <div class="detector-info">
                    <div class="detector-name">{{ getDetectorName(det.detector_name) }}</div>
                    <div class="detector-score">
                      {{ det.score.toFixed(2) }} / {{ det.threshold.toFixed(2) }}
                    </div>
                  </div>
                  <div :class="['detector-status', det.is_abnormal ? 'abnormal' : 'normal']">
                    {{ det.is_abnormal ? '异常' : '正常' }}
                  </div>
                </div>
              </div>
            </div>
            
            <div class="result-suggestions" v-if="imageResult.is_abnormal">
              <h4>💡 改进建议</h4>
              <ul>
                <li v-for="(det, idx) in abnormalDetectors" :key="idx">
                  <strong>{{ getDetectorName(det.detector_name) }}:</strong>
                  {{ det.suggestions?.[0] || det.explanation }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="批量检测" name="batch">
        <div class="batch-content">
          <el-upload
            class="upload-area"
            drag
            multiple
            :auto-upload="false"
            accept="image/*"
            @change="handleBatchChange"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              拖拽多个图像到此处，或 <em>点击上传</em>
            </div>
            <div class="upload-tip">支持批量上传多个图像文件</div>
          </el-upload>
          
          <div v-if="batchFiles.length > 0" class="batch-list">
            <el-table :data="batchFiles" max-height="300">
              <el-table-column prop="name" label="文件名" />
              <el-table-column prop="size" label="大小" width="100">
                <template #default="{ row }">
                  {{ formatSize(row.size) }}
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'success' ? 'success' : row.status === 'error' ? 'danger' : 'info'" size="small">
                    {{ row.statusText }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="batch-actions">
              <el-button @click="clearBatch">清空列表</el-button>
              <el-button type="primary" :loading="loading" @click="startBatchDetection">
                开始批量检测
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="视频检测" name="video">
        <div class="video-content">
          <el-upload
            class="upload-area"
            drag
            :auto-upload="false"
            :show-file-list="false"
            accept="video/*"
            @change="handleVideoChange"
          >
            <template v-if="!currentVideo">
              <el-icon class="upload-icon"><VideoCamera /></el-icon>
              <div class="upload-text">
                拖拽视频到此处，或 <em>点击上传</em>
              </div>
              <div class="upload-tip">支持 MP4、AVI、MOV 格式</div>
            </template>
            <template v-else>
              <div class="video-preview">
                <el-icon :size="48"><VideoCamera /></el-icon>
                <span>{{ currentVideo.name }}</span>
                <span class="video-size">{{ formatSize(currentVideo.size) }}</span>
              </div>
            </template>
          </el-upload>
          
          <div class="upload-options" v-if="currentVideo">
            <el-form label-width="80px" size="small">
              <el-form-item label="采样策略">
                <el-select v-model="videoOptions.sample_strategy">
                  <el-option label="固定间隔" value="interval" />
                  <el-option label="场景变化" value="scene" />
                  <el-option label="混合模式" value="hybrid" />
                </el-select>
              </el-form-item>
              <el-form-item label="采样间隔">
                <el-input-number v-model="videoOptions.sample_interval" :min="0.5" :max="5" :step="0.5" />
                <span class="unit">秒</span>
              </el-form-item>
            </el-form>
            
            <div class="action-buttons">
              <el-button @click="clearVideo">清除</el-button>
              <el-button type="primary" :loading="loading" @click="startVideoDetection">
                开始检测
              </el-button>
            </div>
          </div>
          
          <!-- 视频检测结果 -->
          <div class="result-section" v-if="videoResult">
            <div class="result-header">
              <h3>视频检测结果</h3>
              <span :class="['status-tag', videoResult.is_abnormal ? 'abnormal' : 'normal']">
                {{ videoResult.is_abnormal ? '⚠️ 检测到异常' : '✅ 正常' }}
              </span>
            </div>
            
            <div class="video-info">
              <div class="info-item">
                <span class="label">分辨率:</span>
                <span class="value">{{ videoResult.width }} × {{ videoResult.height }}</span>
              </div>
              <div class="info-item">
                <span class="label">时长:</span>
                <span class="value">{{ videoResult.duration.toFixed(1) }} 秒</span>
              </div>
              <div class="info-item">
                <span class="label">帧率:</span>
                <span class="value">{{ videoResult.fps.toFixed(1) }} fps</span>
              </div>
              <div class="info-item">
                <span class="label">采样帧数:</span>
                <span class="value">{{ videoResult.sampled_frames }}</span>
              </div>
              <div class="info-item">
                <span class="label">整体评分:</span>
                <span class="value">{{ videoResult.overall_score.toFixed(1) }}</span>
              </div>
            </div>
            
            <div class="result-issues" v-if="videoResult.issues?.length">
              <h4>问题时间段</h4>
              <el-timeline>
                <el-timeline-item 
                  v-for="(issue, idx) in videoResult.issues" 
                  :key="idx"
                  :color="issue.severity === 'error' ? '#f56c6c' : '#e6a23c'"
                >
                  <div class="issue-item">
                    <span class="issue-type">{{ getIssueTypeName(issue.issue_type) }}</span>
                    <span class="issue-time">{{ issue.start_time.toFixed(1) }}s - {{ issue.end_time.toFixed(1) }}s</span>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDetectionStore } from '@/stores/detection'
import { ElMessage } from 'element-plus'
import { UploadFilled, VideoCamera } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'

const detectionStore = useDetectionStore()
const activeTab = ref('single')
const loading = ref(false)

// 单图检测
const currentImage = ref<File | null>(null)
const imagePreview = ref('')
const imageResult = ref<any>(null)
const detectOptions = ref({
  profile: 'normal',
  level: 'standard',
})

// 批量检测
const batchFiles = ref<any[]>([])

// 视频检测
const currentVideo = ref<File | null>(null)
const videoResult = ref<any>(null)
const videoOptions = ref({
  sample_strategy: 'interval',
  sample_interval: 1.0,
})

// 检测器映射
const DETECTOR_NAMES: Record<string, { name: string; icon: string }> = {
  blur: { name: '清晰度', icon: '🔍' },
  brightness: { name: '亮度', icon: '☀️' },
  contrast: { name: '对比度', icon: '◐' },
  color: { name: '色彩', icon: '🎨' },
  noise: { name: '噪声', icon: '🔊' },
  stripe: { name: '条纹', icon: '📏' },
  occlusion: { name: '遮挡', icon: '🚧' },
  signal_loss: { name: '信号', icon: '📡' },
  freeze: { name: '画面冻结', icon: '❄️' },
  scene_change: { name: '场景变换', icon: '🔄' },
  shake: { name: '视频抖动', icon: '📳' },
}

const ISSUE_TYPE_NAMES: Record<string, string> = {
  normal: '正常',
  blur: '图像模糊',
  over_bright: '过度曝光',
  under_bright: '曝光不足',
  low_contrast: '对比度过低',
  high_contrast: '对比度过高',
  color_cast: '色彩偏差',
  desaturated: '色彩饱和度低',
  noise: '噪声干扰',
  stripe: '条纹干扰',
  occlusion: '画面遮挡',
  signal_loss: '信号丢失',
  freeze: '画面冻结',
  scene_change: '场景变换异常',
  shake: '视频抖动',
}

const abnormalDetectors = computed(() => {
  return imageResult.value?.detection_results?.filter((d: any) => d.is_abnormal) || []
})

function getDetectorName(name: string) {
  return DETECTOR_NAMES[name]?.name || name
}

function getDetectorIcon(name: string) {
  return DETECTOR_NAMES[name]?.icon || '📊'
}

function getIssueTypeName(type: string) {
  return ISSUE_TYPE_NAMES[type] || type
}

function getSeverityType(severity: string) {
  const map: Record<string, string> = {
    normal: 'success',
    info: 'info',
    warning: 'warning',
    error: 'danger',
  }
  return map[severity] || 'info'
}

function getSeverityName(severity: string) {
  const map: Record<string, string> = {
    normal: '正常',
    info: '提示',
    warning: '警告',
    error: '严重',
  }
  return map[severity] || severity
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function handleImageChange(file: UploadFile) {
  if (file.raw) {
    currentImage.value = file.raw
    imagePreview.value = URL.createObjectURL(file.raw)
    imageResult.value = null
  }
}

function clearImage() {
  currentImage.value = null
  imagePreview.value = ''
  imageResult.value = null
}

async function startDetection() {
  if (!currentImage.value) return
  
  loading.value = true
  try {
    imageResult.value = await detectionStore.diagnoseImage(currentImage.value, detectOptions.value)
  } catch (error) {
    ElMessage.error('检测失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function handleBatchChange(file: UploadFile) {
  if (file.raw) {
    batchFiles.value.push({
      file: file.raw,
      name: file.name,
      size: file.raw.size,
      status: 'pending',
      statusText: '待检测',
    })
  }
}

function clearBatch() {
  batchFiles.value = []
}

async function startBatchDetection() {
  if (batchFiles.value.length === 0) return
  
  loading.value = true
  try {
    const files = batchFiles.value.map(f => f.file)
    await detectionStore.diagnoseBatch(files, detectOptions.value)
    ElMessage.success('批量检测完成')
  } catch (error) {
    ElMessage.error('批量检测失败')
  } finally {
    loading.value = false
  }
}

function handleVideoChange(file: UploadFile) {
  if (file.raw) {
    currentVideo.value = file.raw
    videoResult.value = null
  }
}

function clearVideo() {
  currentVideo.value = null
  videoResult.value = null
}

async function startVideoDetection() {
  if (!currentVideo.value) return
  
  loading.value = true
  try {
    videoResult.value = await detectionStore.diagnoseVideo(currentVideo.value, videoOptions.value)
  } catch (error) {
    ElMessage.error('视频检测失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.detection {
  max-width: 1200px;
  margin: 0 auto;
}

.detection-content,
.batch-content,
.video-content {
  display: grid;
  gap: 24px;
}

.upload-section {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
  
  @media (max-width: 800px) {
    grid-template-columns: 1fr;
  }
}

.upload-area {
  :deep(.el-upload-dragger) {
    width: 100%;
    height: 300px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    border-radius: 12px;
  }
  
  .preview-image {
    max-width: 100%;
    max-height: 280px;
    object-fit: contain;
    border-radius: 8px;
  }
}

.upload-options {
  background: #fff;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  
  .action-buttons {
    margin-top: 20px;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }
  
  .unit {
    margin-left: 8px;
    color: #909399;
  }
}

.result-section {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  
  h3 {
    font-size: 18px;
    font-weight: 600;
  }
}

.result-summary {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: #fef0f0;
  border-radius: 8px;
  margin-bottom: 20px;
  
  .summary-item {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .label {
      color: #909399;
    }
    
    .value {
      font-weight: 600;
      color: #f56c6c;
    }
  }
}

.result-detectors {
  h4 {
    font-size: 14px;
    color: #606266;
    margin-bottom: 16px;
  }
}

.detector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.detector-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid transparent;
  
  &.abnormal {
    background: #fef0f0;
    border-color: #f56c6c;
  }
  
  .detector-icon {
    font-size: 24px;
  }
  
  .detector-info {
    flex: 1;
    
    .detector-name {
      font-weight: 500;
      margin-bottom: 2px;
    }
    
    .detector-score {
      font-size: 12px;
      color: #909399;
    }
  }
  
  .detector-status {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
    
    &.normal {
      background: rgba(103, 194, 58, 0.1);
      color: #67c23a;
    }
    
    &.abnormal {
      background: rgba(245, 108, 108, 0.1);
      color: #f56c6c;
    }
  }
}

.result-suggestions {
  margin-top: 20px;
  padding: 16px;
  background: #f0f9eb;
  border-radius: 8px;
  
  h4 {
    margin-bottom: 12px;
    font-size: 14px;
  }
  
  ul {
    margin: 0;
    padding-left: 20px;
    
    li {
      margin-bottom: 8px;
      color: #606266;
      
      strong {
        color: #303133;
      }
    }
  }
}

.video-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #606266;
  
  .video-size {
    font-size: 12px;
    color: #909399;
  }
}

.video-info {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
  
  .info-item {
    .label {
      font-size: 12px;
      color: #909399;
      display: block;
      margin-bottom: 4px;
    }
    
    .value {
      font-weight: 600;
      color: #303133;
    }
  }
}

.result-issues {
  h4 {
    margin-bottom: 16px;
    font-size: 14px;
  }
  
  .issue-item {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .issue-type {
      font-weight: 500;
    }
    
    .issue-time {
      font-size: 12px;
      color: #909399;
    }
  }
}

.batch-list {
  margin-top: 20px;
  
  .batch-actions {
    margin-top: 16px;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }
}
</style>

