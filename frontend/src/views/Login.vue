<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <el-icon :size="36" color="#409EFF"><View /></el-icon>
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
.login-page { height: 100%; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); }
.login-card { width: 380px; background: #fff; border-radius: 12px; padding: 40px 36px; box-shadow: 0 12px 40px rgba(0,0,0,.3); }
.brand { text-align: center; margin-bottom: 28px; }
.brand h1 { font-size: 20px; margin: 12px 0 6px; color: #303133; }
.brand p { font-size: 13px; color: #909399; }
.btn { width: 100%; }
.tip { text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 12px; }
</style>
