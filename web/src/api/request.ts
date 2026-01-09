import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token 等认证信息
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse) => {
    const data = response.data
    // 后端统一返回格式: {code: 0, message: "success", data: {...}}
    // 如果返回格式符合，提取 data 字段；否则直接返回
    if (data && typeof data === 'object' && 'code' in data && 'data' in data) {
      // 检查 code 是否为成功状态
      if (data.code === 0 || data.code === 200) {
        return data.data
      } else {
        // 如果 code 不是成功状态，抛出错误
        const error = new Error(data.message || '请求失败')
        ;(error as any).code = data.code
        return Promise.reject(error)
      }
    }
    // 兼容其他格式，直接返回
    return data
  },
  (error) => {
    let message = '请求失败'
    
    if (error.response) {
      const { status, data } = error.response
      // 处理 FastAPI 的错误格式
      if (data?.detail) {
        if (typeof data.detail === 'string') {
          message = data.detail
        } else if (data.detail?.message) {
          message = data.detail.message
        } else if (data.detail?.details) {
          message = data.detail.details
        }
      } else if (data?.message) {
        message = data.message
      } else {
        message = `错误 ${status}`
      }
      
      switch (status) {
        case 400:
          message = message || '请求参数错误'
          break
        case 404:
          message = message || '请求的资源不存在'
          break
        case 500:
          message = message || '服务器内部错误'
          break
      }
    } else if (error.message) {
      if (error.message.includes('timeout')) {
        message = '请求超时，请稍后重试'
      } else if (error.message.includes('Network Error')) {
        message = '网络错误，请检查网络连接'
      } else {
        message = error.message
      }
    }
    
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request

// 导出请求方法
export const get = <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  return request.get(url, config)
}

export const post = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
  return request.post(url, data, config)
}

export const put = <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
  return request.put(url, data, config)
}

export const del = <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  return request.delete(url, config)
}

