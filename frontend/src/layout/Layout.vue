<template>
  <el-container class="layout">
    <el-aside width="218px" class="aside">
      <div class="logo">
        <div class="logo-badge"><el-icon :size="18"><View /></el-icon></div>
        <span>寻觅客 · 新零售追踪</span>
      </div>
      <el-menu :default-active="$route.path" router class="side-menu">
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
/* 侧边栏：白底 + 右侧细分割线 */
.aside {
  background: var(--surface);
  border-right: 1px solid var(--border-1);
  box-shadow: 2px 0 12px rgba(43, 75, 110, .03);
  z-index: 5;
}
.logo {
  display: flex; align-items: center; gap: 10px;
  color: var(--text-1); font-weight: 700;
  padding: 20px 18px; font-size: 15px; letter-spacing: .3px;
}
.logo-badge {
  width: 32px; height: 32px; border-radius: 9px; flex: none;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, var(--brand-400), var(--brand-600));
  box-shadow: 0 3px 8px rgba(59, 130, 196, .35);
}

/* 菜单项：胶囊式选中态，浅蓝灰底 + 主色文字 + 左侧指示条 */
.side-menu { padding: 6px 10px; background: transparent; }
.side-menu :deep(.el-menu-item) {
  height: 44px; line-height: 44px;
  margin: 4px 0; border-radius: 8px;
  color: var(--text-2);
  position: relative;
}
.side-menu :deep(.el-menu-item .el-icon) { color: inherit; font-size: 17px; }
.side-menu :deep(.el-menu-item:hover) {
  background: var(--blue-gray-200);
  color: var(--brand-600);
}
.side-menu :deep(.el-menu-item.is-active) {
  background: var(--brand-100);
  color: var(--brand-600);
  font-weight: 600;
}
.side-menu :deep(.el-menu-item.is-active::before) {
  content: ''; position: absolute; left: 0; top: 10px; bottom: 10px;
  width: 3px; border-radius: 2px;
  background: linear-gradient(var(--brand-400), var(--brand-600));
}

.header {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--surface);
  border-bottom: 1px solid var(--border-1);
  box-shadow: 0 1px 6px rgba(43, 75, 110, .04);
  z-index: 4;
}
.title { font-size: 16px; font-weight: 650; color: var(--text-1); }
.right { display: flex; align-items: center; gap: 16px; }
.alarm-tag { cursor: pointer; border-radius: 999px; }
.user { display: flex; align-items: center; gap: 5px; cursor: pointer; color: var(--text-2); outline: none; }
.user:hover { color: var(--brand-600); }
.main {
  background: var(--blue-gray-100);
  overflow-y: auto;
  padding: 18px;
}
</style>
