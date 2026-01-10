import request from './request'

// 流检测相关类型定义
export interface StreamStartRequest {
  stream_url: string
  stream_type?: 'rtsp' | 'rtmp'
  sample_interval?: number
  detection_interval?: number
  config?: Record<string, any>
}

export interface StreamStartResponse {
  stream_id: string
  status: string
  stream_url: string
  started_at: string
}

export interface StreamStatus {
  stream_id: string
  stream_url: string
  stream_type: string
  status: 'running' | 'stopped' | 'error'
  is_connected: boolean
  fps: number
  frames_received: number
  frames_detected: number
  last_detection_time: string | null
  connection_errors: number
  reconnect_count: number
}

export interface StreamResult {
  stream_id: string
  timestamp: string
  is_connected: boolean
  fps: number
  is_abnormal: boolean
  image_detection: any
  video_detection: any
  primary_issue: string | null
  severity: string
}

export interface StreamResultsResponse {
  stream_id: string
  results: StreamResult[]
  total: number
}

// 流检测 API
export const streamApi = {
  // 启动流检测
  startStream(data: StreamStartRequest) {
    return request.post<StreamStartResponse>('/diagnose/stream/start', data)
  },

  // 停止流检测
  stopStream(streamId: string) {
    return request.post(`/diagnose/stream/${streamId}/stop`)
  },

  // 获取流状态
  getStreamStatus(streamId: string) {
    return request.get<StreamStatus>(`/diagnose/stream/${streamId}/status`)
  },

  // 获取流检测结果
  getStreamResults(streamId: string, params?: { limit?: number; since?: string }) {
    return request.get<StreamResultsResponse>(`/diagnose/stream/${streamId}/results`, { params })
  },

  // 列出所有流
  listStreams() {
    return request.get<{ streams: StreamStatus[]; total: number }>('/diagnose/stream/streams')
  },
}

export default streamApi
