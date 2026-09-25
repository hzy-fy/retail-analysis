<template>
  <el-container class="layout">
    <el-aside width="210px" class="aside">
      <div class="logo">
        <el-icon :size="24" color="#409EFF"><View /></el-icon>
        <span>寻觅客 · 新零售追踪</span>
      </div>
      <el-menu :default-active="$route.path" router background-color="#001529" text-color="#a6adb4" active-text-color="#fff">
        <el-menu-item index="/monitor"><el-icon><Monitor /></el-icon><span>实时监控</span></el-menu-item>
        <el-menu-item index="/screen"><el-icon><DataAnalysis /></el-icon><span>数据大屏</span></el-menu-item>
        <el-menu-item index="/roi"><el-icon><Aim /></el-icon><span>ROI 区域管理</span></el-menu-item>
        <el-menu-item index="/history"><el-icon><Clock /></el-icon><span>历史记录</span></el-menu-item>
        <el-menu-item index="/alarms"><el-icon><Bell /></el-icon><span>告警中心</span></el-menu-item>
        <el-menu-item index="/reports"><el-icon><Histogram /></el-icon><span>货架报表</span></el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>系统设置</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title }}</span>
        <div class="right">
          <el-tag v-if="pendingCount > 0" type="danger" effect="dark" class="alarm-tag" @click="$router.push('/alarms')">
            待处理告警 {{ pendingCount }}
          </el-tag>
          <el-dropdown>
            <span class="user">
              <el-icon><User /></el-icon>{{ auth.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="onLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { getAlarms } from '../api'

const auth = useAuthStore()
const router = useRouter()
const pendingCount = ref(0)
let timer: number

async function refreshAlarms() {
  try {
    const res: any = await getAlarms({ status: 'pending' })
    pendingCount.value = res.count ?? res.length ?? 0
  } catch { /* 已统一提示 */ }
}

function onLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  refreshAlarms()
  timer = window.setInterval(refreshAlarms, 30000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.layout { height: 100%; }
.aside { background: #001529; }
.logo { display: flex; align-items: center; gap: 8px; color: #fff; font-weight: 600; padding: 18px 16px; font-size: 15px; }
.aside :deep(.el-menu) { border-right: none; }
.header { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid #eee; }
.title { font-size: 16px; font-weight: 600; }
.right { display: flex; align-items: center; gap: 16px; }
.alarm-tag { cursor: pointer; }
.user { display: flex; align-items: center; gap: 4px; cursor: pointer; }
.main { background: #f0f2f5; overflow-y: auto; }
</style>
