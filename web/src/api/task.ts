import request from './request'

export interface TaskConfig {
  input_path: string
  pattern?: string
  profile?: string
  level?: string
  recursive?: boolean
  sample_rate?: number
}

export interface TaskOutput {
  path: string
  format?: string[]
  keep_days?: number
}

export interface Task {
  id: string
  name: string
  description: string
  task_type: string
  cron_expression: string
  enabled: boolean
  config: TaskConfig
  output: TaskOutput
  created_at?: string
  updated_at?: string
  last_run_at?: string
  next_run_at?: string
}

export interface CreateTaskRequest {
  name: string
  description?: string
  task_type: string
  cron_expression: string
  enabled?: boolean
  config: TaskConfig
  output: TaskOutput
}

export interface UpdateTaskRequest {
  name?: string
  description?: string
  cron_expression?: string
  enabled?: boolean
  config?: Partial<TaskConfig>
  output?: Partial<TaskOutput>
}

export interface Execution {
  id: string
  task_id: string
  task_name: string
  status: string
  started_at?: string
  finished_at?: string
  duration_seconds: number
  total_items: number
  normal_count: number
  abnormal_count: number
  error_count: number
  report_path?: string
  error_message?: string
}

export const taskApi = {
  // 获取任务列表
  getTasks() {
    return request.get<{ tasks: Task[]; total: number }>('/tasks')
  },
  
  // 获取任务详情
  getTask(taskId: string) {
    return request.get<Task>(`/tasks/${taskId}`)
  },
  
  // 创建任务
  createTask(task: CreateTaskRequest) {
    return request.post<Task>('/tasks', task)
  },
  
  // 更新任务
  updateTask(taskId: string, task: Partial<CreateTaskRequest>) {
    return request.put<Task>(`/tasks/${taskId}`, task)
  },
  
  // 删除任务
  deleteTask(taskId: string) {
    return request.delete(`/tasks/${taskId}`)
  },
  
  // 启用任务
  enableTask(taskId: string) {
    return request.post(`/tasks/${taskId}/enable`)
  },
  
  // 禁用任务
  disableTask(taskId: string) {
    return request.post(`/tasks/${taskId}/disable`)
  },
  
  // 立即执行任务
  runTask(taskId: string) {
    return request.post(`/tasks/${taskId}/run`)
  },
  
  // 获取任务执行历史
  getTaskExecutions(taskId: string, limit = 50) {
    return request.get<{ executions: Execution[]; total: number }>(`/tasks/${taskId}/executions`, {
      params: { limit },
    })
  },
  
  // 获取所有执行历史
  getAllExecutions(limit = 50) {
    return request.get<{ executions: Execution[]; total: number }>('/tasks/executions/all', {
      params: { limit },
    })
  },
}

export default taskApi
