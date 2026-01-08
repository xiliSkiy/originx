import request from './request'

// 类型定义
export interface DetectionResult {
  detector_name: string
  is_abnormal: boolean
  score: number
  threshold: number
  confidence: number
  issue_type: string
  explanation: string
  suggestions: string[]
  process_time_ms: number
}

export interface ImageDiagnoseResult {
  image_path: string
  image_size: [number, number]
  is_abnormal: boolean
  primary_issue: string | null
  severity: string
  detection_results: DetectionResult[]
  total_process_time_ms: number
}

export interface VideoDiagnoseResult {
  video_path: string
  video_id: string
  width: number
  height: number
  fps: number
  duration: number
  frame_count: number
  sampled_frames: number
  is_abnormal: boolean
  overall_score: number
  primary_issue: string | null
  severity: string
  issues: any[]
  detection_results: any[]
  process_time_ms: number
}

export interface DetectorInfo {
  name: string
  display_name: string
  description: string
  version: string
  priority: number
  supported_levels: string[]
}

// API 方法
export const diagnosisApi = {
  // 图像检测
  diagnoseImage(file: File, options: { profile?: string; level?: string } = {}) {
    const formData = new FormData()
    formData.append('image', file)
    if (options.profile) formData.append('profile', options.profile)
    if (options.level) formData.append('level', options.level)
    
    return request.post<ImageDiagnoseResult>('/diagnose/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  // 批量图像检测
  diagnoseBatch(files: File[], options: { profile?: string; level?: string } = {}) {
    const formData = new FormData()
    files.forEach(file => formData.append('images', file))
    if (options.profile) formData.append('profile', options.profile)
    if (options.level) formData.append('level', options.level)
    
    return request.post('/diagnose/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  // 视频检测
  diagnoseVideo(file: File, options: {
    profile?: string
    sample_strategy?: string
    sample_interval?: number
  } = {}) {
    const formData = new FormData()
    formData.append('video', file)
    if (options.profile) formData.append('profile', options.profile)
    if (options.sample_strategy) formData.append('sample_strategy', options.sample_strategy)
    if (options.sample_interval) formData.append('sample_interval', String(options.sample_interval))
    
    return request.post<VideoDiagnoseResult>('/video/diagnose', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 视频处理可能需要更长时间
    })
  },
  
  // 获取图像检测器列表
  getImageDetectors() {
    return request.get<DetectorInfo[]>('/detectors')
  },
  
  // 获取视频检测器列表
  getVideoDetectors() {
    return request.get<DetectorInfo[]>('/video/detectors')
  },
}

export default diagnosisApi

