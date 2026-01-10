import request from './request'

// 基准图像相关类型定义
export interface BaselineImage {
  baseline_id: string
  name: string
  description: string
  tags: string[]
  image_path: string
  created_at: string
  image_size: [number, number]
}

export interface BaselineCreateRequest {
  name: string
  description?: string
  tags?: string[]
  image?: File
  image_base64?: string
}

export interface BaselineUpdateRequest {
  name?: string
  description?: string
  tags?: string[]
}

export interface BaselineCompareRequest {
  image?: File
  image_base64?: string
  baseline_id?: string
  baseline_image?: File
  baseline_image_base64?: string
  profile?: string
  level?: string
}

export interface BaselineCompareResult {
  task_id: string
  is_abnormal: boolean
  overall_similarity: number
  comparison_result: {
    ssim_score: number
    histogram_similarity: number
    feature_match_score: number
    region_differences: Array<{
      region: [number, number]
      bbox: [number, number, number, number]
      ssim: number
      is_abnormal: boolean
    }>
  }
  explanation: string
  suggestions: string[]
  detection_results: any[]
  process_time_ms: number
}

// 基准图像 API
export const baselineApi = {
  // 创建基准图像
  createBaseline(data: BaselineCreateRequest) {
    const formData = new FormData()
    formData.append('name', data.name)
    if (data.description) formData.append('description', data.description)
    if (data.tags && data.tags.length > 0) {
      formData.append('tags', data.tags.join(','))
    }
    if (data.image) {
      formData.append('image', data.image)
    } else if (data.image_base64) {
      formData.append('image_base64', data.image_base64)
    }
    
    return request.post<BaselineImage>('/baseline/images', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 列出所有基准图像
  listBaselines() {
    return request.get<{ baselines: BaselineImage[]; total: number }>('/baseline/images')
  },

  // 获取基准图像信息
  getBaseline(baselineId: string) {
    return request.get<BaselineImage>(`/baseline/images/${baselineId}`)
  },

  // 更新基准图像
  updateBaseline(baselineId: string, data: BaselineUpdateRequest) {
    return request.put<BaselineImage>(`/baseline/images/${baselineId}`, data)
  },

  // 删除基准图像
  deleteBaseline(baselineId: string) {
    return request.delete(`/baseline/images/${baselineId}`)
  },

  // 使用基准图像对比检测
  compareWithBaseline(data: BaselineCompareRequest) {
    const formData = new FormData()
    
    if (data.image) {
      formData.append('image', data.image)
    } else if (data.image_base64) {
      formData.append('image_base64', data.image_base64)
    }
    
    if (data.baseline_id) {
      formData.append('baseline_id', data.baseline_id)
    } else if (data.baseline_image) {
      formData.append('baseline_image', data.baseline_image)
    } else if (data.baseline_image_base64) {
      formData.append('baseline_image_base64', data.baseline_image_base64)
    }
    
    if (data.profile) formData.append('profile', data.profile)
    if (data.level) formData.append('level', data.level)
    
    return request.post<BaselineCompareResult>('/baseline/compare', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default baselineApi
