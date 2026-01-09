import request from './request'

// 类型定义
export interface DetectionResult {
  detector_name?: string // 前端期望的字段
  type?: string // 后端返回的字段（issue type）
  issue_type?: string // 兼容字段
  is_abnormal: boolean
  score: number
  threshold: number
  confidence: number
  explanation: string
  suggestions?: string[]
  process_time_ms?: number
}

export interface ImageDiagnoseResult {
  task_id?: string
  image_path?: string
  image_size?: [number, number]
  is_abnormal: boolean
  primary_issue: string | null
  severity: string
  detection_results?: DetectionResult[]
  issues?: DetectionResult[] // 后端可能返回 issues 而不是 detection_results
  total_process_time_ms?: number
  process_time_ms?: number
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
  priority?: number
  supported_levels?: string[]
  suppresses?: string[]
  config?: Record<string, any>
}

// API 方法
export const diagnosisApi = {
  // 图像检测
  diagnoseImage(file: File, options: { profile?: string; level?: string } = {}) {
    const formData = new FormData()
    formData.append('file', file)  // 后端期望的字段名是 'file'
    if (options.profile) formData.append('profile', options.profile)
    if (options.level) formData.append('level', options.level)
    
    return request.post<ImageDiagnoseResult>('/diagnose/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  // 批量图像检测
  // 注意：后端期望 JSON 格式，需要将文件转换为 base64
  async diagnoseBatch(files: File[], options: { profile?: string; level?: string } = {}) {
    // 将文件转换为 base64
    const images = await Promise.all(
      files.map(async (file, index) => {
        const base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            const result = reader.result as string
            // 移除 data:image/xxx;base64, 前缀
            const base64Data = result.split(',')[1]
            resolve(base64Data)
          }
          reader.onerror = reject
          reader.readAsDataURL(file)
        })
        return {
          id: `img_${index}_${Date.now()}`,
          base64: base64,
        }
      })
    )
    
    const payload = {
      images,
      profile: options.profile || 'normal',
      level: options.level || 'fast',
    }
    
    return request.post('/diagnose/batch', payload)
  },
  
  // 视频检测
  diagnoseVideo(file: File, options: {
    profile?: string
    sample_strategy?: string
    sample_interval?: number
    max_frames?: number
  } = {}) {
    const formData = new FormData()
    formData.append('video', file)  // 后端期望的字段名是 'video'
    if (options.profile) formData.append('profile', options.profile)
    if (options.sample_strategy) formData.append('sample_strategy', options.sample_strategy)
    if (options.sample_interval) formData.append('sample_interval', String(options.sample_interval))
    if (options.max_frames) formData.append('max_frames', String(options.max_frames))
    
    return request.post<VideoDiagnoseResult>('/video/diagnose', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 视频处理可能需要更长时间
    })
  },
  
  // 获取图像检测器列表
  // 后端返回格式: {code: 0, message: "success", data: DetectorInfo[]}
  getImageDetectors() {
    return request.get<DetectorInfo[]>('/detectors')
  },
  
  // 获取视频检测器列表
  // 后端返回格式: VideoDetectorInfo[] (直接返回数组，不是包装格式)
  getVideoDetectors() {
    return request.get<DetectorInfo[]>('/video/detectors')
  },
}

export default diagnosisApi

