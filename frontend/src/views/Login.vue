<template>
  <div class="login-page">
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    <div class="login-card">
      <div class="brand">
        <div class="brand-badge"><el-icon :size="30"><View /></el-icon></div>
        <h1>寻觅客 · 新零售追踪</h1>
        <p>视觉智能门店管理平台</p>
      </div>
      <el-form @submit.prevent="onLogin">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" size="large" class="btn" :loading="loading" native-type="submit">登 录</el-button>
        <p class="tip">演示账号：admin / admin123</p>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../store/auth'

const username = ref('admin')
const password = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function onLogin() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push((route.query.redirect as string) || '/')
  } catch { /* 拦截器已提示 */ } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 浅蓝灰 → 白 的柔和渐变 + 两团模糊光斑做点缀（15%） */
.login-page {
  position: relative; height: 100%; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(150deg, #ffffff 0%, #f3f7fb 45%, #e7eff7 100%);
}
.blob { position: absolute; border-radius: 50%; filter: blur(70px); opacity: .55; pointer-events: none; }
.blob-1 { width: 420px; height: 420px; top: -140px; right: -100px;
  background: radial-gradient(circle, #9dc1e2, transparent 70%); }
.blob-2 { width: 360px; height: 360px; bottom: -130px; left: -90px;
  background: radial-gradient(circle, #c6dcef, transparent 70%); }
.login-card {
  position: relative; width: 392px; background: rgba(255, 255, 255, .92);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-1);
  border-radius: 16px; padding: 42px 38px;
  box-shadow: var(--shadow-pop);
}
.brand { text-align: center; margin-bottom: 30px; }
.brand-badge {
  width: 56px; height: 56px; margin: 0 auto;
  border-radius: 16px; display: flex; align-items: center; justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, var(--brand-400), var(--brand-600));
  box-shadow: 0 8px 20px rgba(59, 130, 196, .3);
}
.brand h1 { font-size: 20px; margin: 16px 0 6px; color: var(--text-1); font-weight: 700; }
.brand p { font-size: 13px; color: var(--text-3); }
.btn { width: 100%; height: 42px; font-size: 15px; letter-spacing: 4px;
  background: linear-gradient(135deg, var(--brand-500), var(--brand-600));
  border: none; box-shadow: 0 4px 12px rgba(59, 130, 196, .3); }
.btn:hover { opacity: .92; }
.tip { text-align: center; color: var(--text-3); font-size: 12px; margin-top: 14px; }
</style>
