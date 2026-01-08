<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <!-- 顶部导航 -->
      <header class="app-header">
        <div class="header-left">
          <div class="logo">
            <el-icon :size="28"><VideoCamera /></el-icon>
            <span class="logo-text">OriginX</span>
          </div>
        </div>
        
        <nav class="header-nav">
          <router-link 
            v-for="item in navItems" 
            :key="item.path"
            :to="item.path" 
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </router-link>
        </nav>
        
        <div class="header-right">
          <el-dropdown>
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="User" />
              <span class="username">管理员</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人设置</el-dropdown-item>
                <el-dropdown-item divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      
      <!-- 主内容区 -->
      <main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { 
  DataAnalysis, 
  Monitor, 
  Calendar, 
  Setting, 
  User,
  ArrowDown,
  VideoCamera
} from '@element-plus/icons-vue'

const route = useRoute()

const navItems = [
  { path: '/', title: '仪表盘', icon: DataAnalysis },
  { path: '/detection', title: '检测中心', icon: Monitor },
  { path: '/tasks', title: '任务管理', icon: Calendar },
  { path: '/settings', title: '系统设置', icon: Setting },
]

const isActive = (path: string) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}
</script>

<style lang="scss" scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.app-header {
  height: 60px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  display: flex;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  
  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #fff;
    
    .el-icon {
      color: #409eff;
    }
    
    .logo-text {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 1px;
    }
  }
}

.header-nav {
  flex: 1;
  display: flex;
  justify-content: center;
  gap: 8px;
  
  .nav-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 20px;
    color: rgba(255, 255, 255, 0.7);
    text-decoration: none;
    border-radius: 8px;
    transition: all 0.3s;
    font-size: 14px;
    
    &:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.1);
    }
    
    &.active {
      color: #fff;
      background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
    }
  }
}

.header-right {
  .user-dropdown {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    color: #fff;
    
    .username {
      font-size: 14px;
    }
  }
}

.app-main {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

// 页面过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

