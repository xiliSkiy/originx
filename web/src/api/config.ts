import request from './request'

export interface ConfigProfile {
  name: string
  display_name: string
  description: string
  thresholds: Record<string, number>
}

export interface SystemInfo {
  version: string
  python_version: string
  opencv_version: string
  platform: string
  gpu_available: boolean
  detectors_count: number
}

export const configApi = {
  // 获取当前配置
  getConfig() {
    return request.get('/config')
  },
  
  // 更新配置
  updateConfig(config: Record<string, any>) {
    return request.put('/config', config)
  },
  
  // 获取配置模板列表
  getProfiles() {
    return request.get<ConfigProfile[]>('/config/profiles')
  },
  
  // 应用配置模板
  applyProfile(profileName: string) {
    return request.post(`/config/profiles/${profileName}/apply`)
  },
  
  // 获取系统信息
  getSystemInfo() {
    return request.get<SystemInfo>('/info')
  },
  
  // 健康检查
  healthCheck() {
    return request.get('/health')
  },
}

export default configApi

