<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>仪表盘</h1>
      <p>系统运行状态概览</p>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon primary">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-value">{{ stats.todayTotal }}</div>
        <div class="stat-label">今日检测</div>
        <div class="stat-trend up">
          <el-icon><Top /></el-icon>
          较昨日 +12%
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon warning">
          <el-icon><WarningFilled /></el-icon>
        </div>
        <div class="stat-value">{{ stats.todayAbnormal }}</div>
        <div class="stat-label">今日异常</div>
        <div class="stat-trend down">
          <el-icon><Bottom /></el-icon>
          较昨日 -5%
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon success">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-value">{{ normalRate }}%</div>
        <div class="stat-label">正常率</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon danger">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="stat-value">{{ avgProcessTime }}ms</div>
        <div class="stat-label">平均耗时</div>
      </div>
    </div>
    
    <!-- 图表区域 -->
    <div class="chart-grid">
      <div class="card chart-card">
        <div class="card-header">
          <h3>
            <el-icon><TrendCharts /></el-icon>
            检测趋势
          </h3>
          <el-radio-group v-model="trendRange" size="small">
            <el-radio-button label="week">本周</el-radio-button>
            <el-radio-button label="month">本月</el-radio-button>
          </el-radio-group>
        </div>
        <div class="chart-container" ref="trendChartRef"></div>
      </div>
      
      <div class="card chart-card">
        <div class="card-header">
          <h3>
            <el-icon><PieChart /></el-icon>
            异常类型分布
          </h3>
        </div>
        <div class="chart-container" ref="pieChartRef"></div>
      </div>
    </div>
    
    <!-- 最近检测记录 -->
    <div class="card">
      <div class="card-header">
        <h3>
          <el-icon><Clock /></el-icon>
          最近检测记录
        </h3>
        <el-button text type="primary" @click="$router.push('/detection')">
          查看更多
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      
      <el-table :data="recentRecords" stripe style="width: 100%">
        <el-table-column prop="filename" label="文件名" min-width="200" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.type === 'image' ? 'primary' : 'success'" size="small">
              {{ row.type === 'image' ? '图像' : '视频' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.isAbnormal ? 'abnormal' : 'normal']">
              {{ row.isAbnormal ? '异常' : '正常' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="issue" label="主要问题" width="150">
          <template #default="{ row }">
            {{ row.issue || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="processTime" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.processTime.toFixed(1) }}ms
          </template>
        </el-table-column>
        <el-table-column prop="time" label="检测时间" width="180" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDetectionStore } from '@/stores/detection'
import * as echarts from 'echarts'
import { 
  Document, 
  WarningFilled, 
  CircleCheck, 
  Timer,
  TrendCharts,
  PieChart,
  Clock,
  ArrowRight,
  Top,
  Bottom
} from '@element-plus/icons-vue'

const detectionStore = useDetectionStore()
const trendRange = ref('week')
const trendChartRef = ref<HTMLElement>()
const pieChartRef = ref<HTMLElement>()

// 模拟统计数据
const stats = ref({
  todayTotal: 1286,
  todayAbnormal: 23,
  weekTotal: 8542,
  weekAbnormal: 156,
})

const normalRate = computed(() => {
  if (stats.value.todayTotal === 0) return 100
  return ((1 - stats.value.todayAbnormal / stats.value.todayTotal) * 100).toFixed(1)
})

const avgProcessTime = ref(32.5)

// 模拟最近记录
const recentRecords = ref([
  { filename: 'camera_001_20240108.jpg', type: 'image', isAbnormal: false, issue: null, processTime: 28.5, time: '2024-01-08 14:32:15' },
  { filename: 'camera_002_20240108.jpg', type: 'image', isAbnormal: true, issue: '噪声干扰', processTime: 35.2, time: '2024-01-08 14:30:22' },
  { filename: 'video_entrance.mp4', type: 'video', isAbnormal: true, issue: '画面冻结', processTime: 1250.8, time: '2024-01-08 14:25:10' },
  { filename: 'camera_003_20240108.jpg', type: 'image', isAbnormal: false, issue: null, processTime: 25.1, time: '2024-01-08 14:22:45' },
  { filename: 'camera_004_20240108.jpg', type: 'image', isAbnormal: false, issue: null, processTime: 30.8, time: '2024-01-08 14:20:18' },
])

onMounted(() => {
  initTrendChart()
  initPieChart()
})

function initTrendChart() {
  if (!trendChartRef.value) return
  
  const chart = echarts.init(trendChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['检测总数', '异常数量'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    },
    yAxis: [
      {
        type: 'value',
        name: '检测数量',
        splitLine: { lineStyle: { type: 'dashed' } }
      }
    ],
    series: [
      {
        name: '检测总数',
        type: 'bar',
        data: [1200, 1350, 1180, 1420, 1380, 850, 680],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409EFF' },
            { offset: 1, color: '#79bbff' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '异常数量',
        type: 'line',
        data: [20, 28, 15, 32, 25, 12, 8],
        itemStyle: { color: '#f56c6c' },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 8
      }
    ]
  }
  
  chart.setOption(option)
  window.addEventListener('resize', () => chart.resize())
}

function initPieChart() {
  if (!pieChartRef.value) return
  
  const chart = echarts.init(pieChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center'
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
        },
        data: [
          { value: 35, name: '噪声干扰', itemStyle: { color: '#409EFF' } },
          { value: 28, name: '画面模糊', itemStyle: { color: '#67C23A' } },
          { value: 22, name: '亮度异常', itemStyle: { color: '#E6A23C' } },
          { value: 15, name: '颜色偏差', itemStyle: { color: '#F56C6C' } },
          { value: 10, name: '画面冻结', itemStyle: { color: '#909399' } },
          { value: 8, name: '其他', itemStyle: { color: '#B88230' } },
        ]
      }
    ]
  }
  
  chart.setOption(option)
  window.addEventListener('resize', () => chart.resize())
}
</script>

<style lang="scss" scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
  
  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 600px) {
    grid-template-columns: 1fr;
  }
}

.chart-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
  
  @media (max-width: 1000px) {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  .chart-container {
    height: 300px;
  }
}
</style>

