<template>
  <div class="tasks">
    <div class="page-header">
      <h1>任务管理</h1>
      <p>管理定时检测任务和查看执行历史</p>
    </div>
    
    <!-- 工具栏 -->
    <div class="toolbar card">
      <el-button type="primary" @click="showTaskDialog = true">
        <el-icon><Plus /></el-icon>
        新建任务
      </el-button>
      <el-button @click="refreshTasks">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <!-- 任务列表 -->
    <div class="card">
      <div class="card-header">
        <h3>
          <el-icon><Calendar /></el-icon>
          定时任务
        </h3>
      </div>
      
      <el-table :data="tasks" stripe style="width: 100%">
        <el-table-column prop="name" label="任务名称" min-width="150" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getTaskTypeName(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cron" label="Cron表达式" width="150">
          <template #default="{ row }">
            <code>{{ row.cron }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" size="small" @change="toggleTask(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="lastRun" label="上次执行" width="180">
          <template #default="{ row }">
            {{ row.lastRun || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="nextRun" label="下次执行" width="180">
          <template #default="{ row }">
            {{ row.nextRun || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="runTask(row)">
              立即执行
            </el-button>
            <el-button text type="primary" size="small" @click="editTask(row)">
              编辑
            </el-button>
            <el-button text type="danger" size="small" @click="deleteTask(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 执行历史 -->
    <div class="card">
      <div class="card-header">
        <h3>
          <el-icon><Clock /></el-icon>
          执行历史
        </h3>
      </div>
      
      <el-table :data="executions" stripe style="width: 100%">
        <el-table-column prop="time" label="执行时间" width="180" />
        <el-table-column prop="taskName" label="任务名称" min-width="150" />
        <el-table-column prop="status" label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="检测数" width="100" />
        <el-table-column prop="abnormal" label="异常数" width="100">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.abnormal > 0 }">{{ row.abnormal }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="viewReport(row)">
              查看报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="10"
          :total="100"
          layout="total, prev, pager, next"
        />
      </div>
    </div>
    
    <!-- 新建/编辑任务对话框 -->
    <el-dialog
      v-model="showTaskDialog"
      :title="editingTask ? '编辑任务' : '新建任务'"
      width="600px"
    >
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="taskForm.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="taskForm.description" type="textarea" placeholder="请输入任务描述" />
        </el-form-item>
        <el-form-item label="任务类型" required>
          <el-select v-model="taskForm.type" style="width: 100%">
            <el-option label="批量检测" value="batch" />
            <el-option label="抽样检测" value="sample" />
            <el-option label="视频检测" value="video" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron表达式" required>
          <el-input v-model="taskForm.cron" placeholder="0 2 * * *">
            <template #append>
              <el-button @click="showCronHelper = true">帮助</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="输入路径" required>
          <el-input v-model="taskForm.inputPath" placeholder="/data/images/" />
        </el-form-item>
        <el-form-item label="文件模式">
          <el-input v-model="taskForm.pattern" placeholder="*.jpg" />
        </el-form-item>
        <el-form-item label="配置模板">
          <el-select v-model="taskForm.profile" style="width: 100%">
            <el-option label="严格模式" value="strict" />
            <el-option label="标准模式" value="normal" />
            <el-option label="宽松模式" value="loose" />
          </el-select>
        </el-form-item>
        <el-form-item label="立即启用">
          <el-switch v-model="taskForm.enabled" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showTaskDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTask">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- Cron 帮助对话框 -->
    <el-dialog v-model="showCronHelper" title="Cron表达式帮助" width="500px">
      <div class="cron-help">
        <pre>
┌───────────── 分钟 (0-59)
│ ┌───────────── 小时 (0-23)
│ │ ┌───────────── 日 (1-31)
│ │ │ ┌───────────── 月 (1-12)
│ │ │ │ ┌───────────── 星期 (0-6, 0=周日)
│ │ │ │ │
* * * * *
        </pre>
        
        <h4>常用示例：</h4>
        <ul>
          <li><code>0 2 * * *</code> - 每天凌晨2点</li>
          <li><code>0 */4 * * *</code> - 每4小时</li>
          <li><code>0 9,18 * * 1-5</code> - 工作日9点和18点</li>
          <li><code>*/10 * * * *</code> - 每10分钟</li>
        </ul>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Calendar, Clock } from '@element-plus/icons-vue'

const tasks = ref([
  { id: '1', name: '每日巡检', type: 'batch', cron: '0 2 * * *', enabled: true, lastRun: '2024-01-08 02:00:00', nextRun: '2024-01-09 02:00:00' },
  { id: '2', name: '高峰期抽检', type: 'sample', cron: '0 9,18 * * 1-5', enabled: true, lastRun: '2024-01-08 09:00:00', nextRun: '2024-01-08 18:00:00' },
  { id: '3', name: '视频监控检测', type: 'video', cron: '0 */4 * * *', enabled: false, lastRun: '2024-01-07 20:00:00', nextRun: '-' },
])

const executions = ref([
  { id: '1', time: '2024-01-08 09:00:00', taskName: '高峰期抽检', status: 'success', total: 100, abnormal: 3, duration: 180 },
  { id: '2', time: '2024-01-08 02:00:00', taskName: '每日巡检', status: 'success', total: 1000, abnormal: 12, duration: 3200 },
  { id: '3', time: '2024-01-07 18:00:00', taskName: '高峰期抽检', status: 'success', total: 100, abnormal: 5, duration: 165 },
  { id: '4', time: '2024-01-07 09:00:00', taskName: '高峰期抽检', status: 'failed', total: 0, abnormal: 0, duration: 0 },
])

const currentPage = ref(1)
const showTaskDialog = ref(false)
const showCronHelper = ref(false)
const editingTask = ref<any>(null)
const taskForm = ref({
  name: '',
  description: '',
  type: 'batch',
  cron: '0 2 * * *',
  inputPath: '/data/images/',
  pattern: '*.jpg',
  profile: 'normal',
  enabled: true,
})

function getTaskTypeName(type: string) {
  const map: Record<string, string> = {
    batch: '批量检测',
    sample: '抽样检测',
    video: '视频检测',
  }
  return map[type] || type
}

function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
}

function refreshTasks() {
  ElMessage.success('刷新成功')
}

function toggleTask(task: any) {
  ElMessage.success(task.enabled ? '任务已启用' : '任务已禁用')
}

function runTask(task: any) {
  ElMessageBox.confirm(`确定要立即执行任务"${task.name}"吗？`, '确认', {
    type: 'warning',
  }).then(() => {
    ElMessage.success('任务已开始执行')
  }).catch(() => {})
}

function editTask(task: any) {
  editingTask.value = task
  taskForm.value = { ...task }
  showTaskDialog.value = true
}

function deleteTask(task: any) {
  ElMessageBox.confirm(`确定要删除任务"${task.name}"吗？`, '确认删除', {
    type: 'danger',
  }).then(() => {
    const idx = tasks.value.findIndex(t => t.id === task.id)
    if (idx > -1) tasks.value.splice(idx, 1)
    ElMessage.success('删除成功')
  }).catch(() => {})
}

function saveTask() {
  if (!taskForm.value.name || !taskForm.value.cron) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  if (editingTask.value) {
    Object.assign(editingTask.value, taskForm.value)
    ElMessage.success('更新成功')
  } else {
    tasks.value.push({
      ...taskForm.value,
      id: Date.now().toString(),
      lastRun: null,
      nextRun: '计算中...',
    })
    ElMessage.success('创建成功')
  }
  
  showTaskDialog.value = false
  editingTask.value = null
  taskForm.value = {
    name: '',
    description: '',
    type: 'batch',
    cron: '0 2 * * *',
    inputPath: '/data/images/',
    pattern: '*.jpg',
    profile: 'normal',
    enabled: true,
  }
}

function viewReport(execution: any) {
  ElMessage.info('查看报告功能开发中')
}
</script>

<style lang="scss" scoped>
.tasks {
  max-width: 1400px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}

.cron-help {
  pre {
    background: #f5f7fa;
    padding: 16px;
    border-radius: 8px;
    font-size: 12px;
    line-height: 1.5;
    overflow-x: auto;
  }
  
  h4 {
    margin: 16px 0 8px;
  }
  
  ul {
    padding-left: 20px;
    
    li {
      margin-bottom: 8px;
      
      code {
        margin-right: 8px;
      }
    }
  }
}
</style>

