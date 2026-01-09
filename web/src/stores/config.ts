import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configApi, type SystemInfo } from '@/api/config'

export const useConfigStore = defineStore('config', () => {
  // 状态
  const systemInfo = ref<SystemInfo | null>(null)
  const profiles = ref<any[]>([])
  const currentProfile = ref('normal')
  const thresholds = ref<Record<string, number>>({})
  
  // 操作
  async function loadSystemInfo() {
    try {
      systemInfo.value = await configApi.getSystemInfo()
    } catch (error) {
      console.error('Failed to load system info:', error)
      throw error
    }
  }
  
  async function loadProfiles() {
    try {
      profiles.value = await configApi.getProfiles()
    } catch (error) {
      console.error('Failed to load profiles:', error)
    }
  }
  
  async function applyProfile(profileName: string) {
    try {
      await configApi.applyProfile(profileName)
      currentProfile.value = profileName
    } catch (error) {
      console.error('Failed to apply profile:', error)
      throw error
    }
  }
  
  async function updateThresholds(newThresholds: Record<string, number>) {
    try {
      await configApi.updateConfig({ thresholds: newThresholds })
      thresholds.value = { ...thresholds.value, ...newThresholds }
    } catch (error) {
      console.error('Failed to update thresholds:', error)
      throw error
    }
  }
  
  return {
    systemInfo,
    profiles,
    currentProfile,
    thresholds,
    loadSystemInfo,
    loadProfiles,
    applyProfile,
    updateThresholds,
  }
})

