import { defineStore } from 'pinia'
import { ref } from 'vue'
import { diagnosisApi, type ImageDiagnoseResult, type VideoDiagnoseResult } from '@/api/detection'

export const useDetectionStore = defineStore('detection', () => {
  // 状态
  const loading = ref(false)
  const imageResults = ref<ImageDiagnoseResult[]>([])
  const videoResults = ref<VideoDiagnoseResult[]>([])
  const currentResult = ref<ImageDiagnoseResult | VideoDiagnoseResult | null>(null)
  
  // 统计数据
  const stats = ref({
    todayTotal: 0,
    todayAbnormal: 0,
    weekTotal: 0,
    weekAbnormal: 0,
  })
  
  // 操作
  async function diagnoseImage(file: File, options = {}) {
    loading.value = true
    try {
      const result = await diagnosisApi.diagnoseImage(file, options)
      imageResults.value.unshift(result)
      currentResult.value = result
      updateStats(result)
      return result
    } finally {
      loading.value = false
    }
  }
  
  async function diagnoseBatch(files: File[], options = {}) {
    loading.value = true
    try {
      const result = await diagnosisApi.diagnoseBatch(files, options)
      return result
    } finally {
      loading.value = false
    }
  }
  
  async function diagnoseVideo(file: File, options = {}) {
    loading.value = true
    try {
      const result = await diagnosisApi.diagnoseVideo(file, options)
      videoResults.value.unshift(result)
      currentResult.value = result
      return result
    } finally {
      loading.value = false
    }
  }
  
  function updateStats(result: ImageDiagnoseResult | VideoDiagnoseResult) {
    stats.value.todayTotal++
    stats.value.weekTotal++
    if (result.is_abnormal) {
      stats.value.todayAbnormal++
      stats.value.weekAbnormal++
    }
  }
  
  function clearResults() {
    imageResults.value = []
    videoResults.value = []
    currentResult.value = null
  }
  
  return {
    loading,
    imageResults,
    videoResults,
    currentResult,
    stats,
    diagnoseImage,
    diagnoseBatch,
    diagnoseVideo,
    clearResults,
  }
})

