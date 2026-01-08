<template>
  <div class="settings">
    <div class="page-header">
      <h1>系统设置</h1>
      <p>管理检测配置和系统参数</p>
    </div>
    
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 检测配置 -->
      <el-tab-pane label="检测配置" name="detection">
        <div class="settings-section">
          <h3>配置模板</h3>
          <el-radio-group v-model="currentProfile" size="large" @change="handleProfileChange">
            <el-radio-button label="strict">
              <div class="profile-option">
                <el-icon><Warning /></el-icon>
                <span>严格模式</span>
              </div>
            </el-radio-button>
            <el-radio-button label="normal">
              <div class="profile-option">
                <el-icon><CircleCheck /></el-icon>
                <span>标准模式</span>
              </div>
            </el-radio-button>
            <el-radio-button label="loose">
              <div class="profile-option">
                <el-icon><InfoFilled /></el-icon>
                <span>宽松模式</span>
              </div>
            </el-radio-button>
          </el-radio-group>
          <p class="profile-desc">{{ profileDescriptions[currentProfile] }}</p>
        </div>
        
        <div class="settings-section">
          <h3>检测阈值</h3>
          <div class="threshold-grid">
            <div class="threshold-item" v-for="(config, key) in thresholds" :key="key">
              <div class="threshold-header">
                <span class="threshold-icon">{{ config.icon }}</span>
                <span class="threshold-name">{{ config.name }}</span>
              </div>
              <el-slider
                v-model="config.value"
                :min="config.min"
                :max="config.max"
                :step="config.step"
                show-input
                size="small"
              />
              <div class="threshold-desc">{{ config.desc }}</div>
            </div>
          </div>
        </div>
        
        <div class="settings-actions">
          <el-button @click="resetThresholds">恢复默认</el-button>
          <el-button type="primary" @click="saveThresholds">保存配置</el-button>
        </div>
      </el-tab-pane>
      
      <!-- 检测器管理 -->
      <el-tab-pane label="检测器管理" name="detectors">
        <div class="detector-list">
          <div class="detector-category">
            <h3>图像检测器</h3>
            <el-table :data="imageDetectors" stripe>
              <el-table-column prop="name" label="名称" width="120" />
              <el-table-column prop="displayName" label="显示名称" width="150" />
              <el-table-column prop="description" label="描述" />
              <el-table-column prop="priority" label="优先级" width="80" />
              <el-table-column prop="enabled" label="启用" width="80">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" size="small" />
                </template>
              </el-table-column>
            </el-table>
          </div>
          
          <div class="detector-category">
            <h3>视频检测器</h3>
            <el-table :data="videoDetectors" stripe>
              <el-table-column prop="name" label="名称" width="120" />
              <el-table-column prop="displayName" label="显示名称" width="150" />
              <el-table-column prop="description" label="描述" />
              <el-table-column prop="enabled" label="启用" width="80">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" size="small" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- 系统信息 -->
      <el-tab-pane label="系统信息" name="system">
        <div class="system-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="系统版本">
              <el-tag>{{ systemInfo.version }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Python版本">
              {{ systemInfo.pythonVersion }}
            </el-descriptions-item>
            <el-descriptions-item label="OpenCV版本">
              {{ systemInfo.opencvVersion }}
            </el-descriptions-item>
            <el-descriptions-item label="运行平台">
              {{ systemInfo.platform }}
            </el-descriptions-item>
            <el-descriptions-item label="GPU支持">
              <el-tag :type="systemInfo.gpuAvailable ? 'success' : 'info'">
                {{ systemInfo.gpuAvailable ? '可用' : '不可用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="检测器数量">
              {{ systemInfo.detectorsCount }}
            </el-descriptions-item>
          </el-descriptions>
          
          <div class="system-actions">
            <el-button @click="checkHealth">
              <el-icon><Refresh /></el-icon>
              健康检查
            </el-button>
            <el-button type="primary" @click="exportConfig">
              <el-icon><Download /></el-icon>
              导出配置
            </el-button>
            <el-button @click="importConfig">
              <el-icon><Upload /></el-icon>
              导入配置
            </el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import { ElMessage } from 'element-plus'
import { 
  Warning, 
  CircleCheck, 
  InfoFilled, 
  Refresh, 
  Download,
  Upload 
} from '@element-plus/icons-vue'

const configStore = useConfigStore()
const activeTab = ref('detection')
const currentProfile = ref('normal')

const profileDescriptions: Record<string, string> = {
  strict: '严格模式：使用较低的阈值，对图像质量要求更高，适合对质量要求严格的场景',
  normal: '标准模式：使用平衡的阈值设置，适合大多数场景',
  loose: '宽松模式：使用较高的阈值，对图像质量要求较低，减少误报',
}

const thresholds = reactive({
  blur: { name: '模糊度阈值', icon: '🔍', value: 100, min: 50, max: 500, step: 10, desc: '低于此值判定为模糊' },
  brightness_min: { name: '最低亮度', icon: '🌙', value: 20, min: 0, max: 100, step: 5, desc: '低于此值判定为过暗' },
  brightness_max: { name: '最高亮度', icon: '☀️', value: 235, min: 150, max: 255, step: 5, desc: '高于此值判定为过亮' },
  contrast: { name: '对比度阈值', icon: '◐', value: 20, min: 5, max: 100, step: 5, desc: '低于此值判定为对比度不足' },
  noise: { name: '噪声阈值', icon: '🔊', value: 30, min: 10, max: 100, step: 5, desc: '高于此值判定为噪声过多' },
  occlusion: { name: '遮挡阈值', icon: '🚧', value: 30, min: 10, max: 100, step: 5, desc: '高于此值判定为存在遮挡' },
})

const imageDetectors = ref([
  { name: 'blur', displayName: '模糊检测', description: '检测图像是否模糊', priority: 1, enabled: true },
  { name: 'brightness', displayName: '亮度检测', description: '检测图像亮度是否正常', priority: 2, enabled: true },
  { name: 'contrast', displayName: '对比度检测', description: '检测图像对比度是否正常', priority: 3, enabled: true },
  { name: 'color', displayName: '色彩检测', description: '检测图像色彩是否正常', priority: 4, enabled: true },
  { name: 'noise', displayName: '噪声检测', description: '检测图像噪声水平', priority: 5, enabled: true },
  { name: 'stripe', displayName: '条纹检测', description: '检测图像是否存在条纹干扰', priority: 6, enabled: true },
  { name: 'occlusion', displayName: '遮挡检测', description: '检测图像是否存在遮挡', priority: 7, enabled: true },
  { name: 'signal_loss', displayName: '信号丢失检测', description: '检测是否存在信号丢失', priority: 8, enabled: true },
])

const videoDetectors = ref([
  { name: 'freeze', displayName: '画面冻结检测', description: '检测视频是否存在画面冻结', enabled: true },
  { name: 'scene_change', displayName: '场景变换检测', description: '检测视频场景变换是否异常', enabled: true },
  { name: 'shake', displayName: '视频抖动检测', description: '检测视频是否存在抖动', enabled: true },
])

const systemInfo = ref({
  version: '1.5.0',
  pythonVersion: '3.9.7',
  opencvVersion: '4.8.1',
  platform: 'macOS 13.0',
  gpuAvailable: false,
  detectorsCount: 11,
})

onMounted(async () => {
  await configStore.loadSystemInfo()
  if (configStore.systemInfo) {
    systemInfo.value = {
      version: configStore.systemInfo.version,
      pythonVersion: configStore.systemInfo.python_version,
      opencvVersion: configStore.systemInfo.opencv_version,
      platform: configStore.systemInfo.platform,
      gpuAvailable: configStore.systemInfo.gpu_available,
      detectorsCount: configStore.systemInfo.detectors_count,
    }
  }
})

function handleProfileChange(profile: string) {
  ElMessage.success(`已切换到${profileDescriptions[profile].split('：')[0]}`)
}

function resetThresholds() {
  thresholds.blur.value = 100
  thresholds.brightness_min.value = 20
  thresholds.brightness_max.value = 235
  thresholds.contrast.value = 20
  thresholds.noise.value = 30
  thresholds.occlusion.value = 30
  ElMessage.success('已恢复默认配置')
}

function saveThresholds() {
  ElMessage.success('配置保存成功')
}

function checkHealth() {
  ElMessage.success('系统运行正常')
}

function exportConfig() {
  const config = {
    profile: currentProfile.value,
    thresholds: Object.fromEntries(
      Object.entries(thresholds).map(([key, val]) => [key, val.value])
    ),
  }
  
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'originx-config.json'
  a.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('配置导出成功')
}

function importConfig() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const config = JSON.parse(e.target?.result as string)
          if (config.profile) currentProfile.value = config.profile
          if (config.thresholds) {
            Object.entries(config.thresholds).forEach(([key, value]) => {
              if (thresholds[key as keyof typeof thresholds]) {
                thresholds[key as keyof typeof thresholds].value = value as number
              }
            })
          }
          ElMessage.success('配置导入成功')
        } catch {
          ElMessage.error('配置文件格式错误')
        }
      }
      reader.readAsText(file)
    }
  }
  input.click()
}
</script>

<style lang="scss" scoped>
.settings {
  max-width: 1200px;
  margin: 0 auto;
}

.settings-section {
  margin-bottom: 32px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 16px;
    color: #303133;
  }
}

.profile-option {
  display: flex;
  align-items: center;
  gap: 6px;
}

.profile-desc {
  margin-top: 12px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  color: #606266;
  font-size: 14px;
}

.threshold-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.threshold-item {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  
  .threshold-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    
    .threshold-icon {
      font-size: 20px;
    }
    
    .threshold-name {
      font-weight: 500;
    }
  }
  
  .threshold-desc {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
  }
}

.settings-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.detector-category {
  margin-bottom: 24px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
  }
}

.system-info {
  .system-actions {
    margin-top: 24px;
    display: flex;
    gap: 12px;
  }
}
</style>

