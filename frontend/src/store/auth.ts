import { defineStore } from 'pinia'
import request from '../api/request'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    username: localStorage.getItem('username') || '',
  }),
  actions: {
    async login(username: string, password: string) {
      const res: any = await request.post('/auth/login/', { username, password })
      this.token = res.token
      this.username = res.username
      localStorage.setItem('token', res.token)
      localStorage.setItem('username', res.username)
    },
    logout() {
      this.token = ''
      this.username = ''
      localStorage.removeItem('token')
      localStorage.removeItem('username')
    },
  },
})
