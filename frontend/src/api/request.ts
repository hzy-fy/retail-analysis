import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Token ${token}`
  return config
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请检查后端服务')
    } else if (err.response?.status === 401) {
      localStorage.removeItem('token')
      router.push({ name: 'Login' })
      ElMessage.warning('登录已失效，请重新登录')
    } else {
      ElMessage.error(err.response?.data?.detail || '接口请求失败')
    }
    return Promise.reject(err)
  }
)

export default request
