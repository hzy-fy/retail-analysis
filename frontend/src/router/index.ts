import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('../layout/Layout.vue'),
      redirect: '/monitor',
      children: [
        { path: 'monitor', name: 'Monitor', component: () => import('../views/Monitor.vue'), meta: { title: '实时监控' } },
        { path: 'screen', name: 'Screen', component: () => import('../views/Screen.vue'), meta: { title: '数据大屏' } },
        { path: 'roi', name: 'RoiManager', component: () => import('../views/RoiManager.vue'), meta: { title: 'ROI 区域管理' } },
        { path: 'history', name: 'History', component: () => import('../views/History.vue'), meta: { title: '历史记录' } },
        { path: 'alarms', name: 'Alarms', component: () => import('../views/Alarms.vue'), meta: { title: '告警中心' } },
        { path: 'reports', name: 'Reports', component: () => import('../views/Reports.vue'), meta: { title: '货架报表' } },
        { path: 'settings', name: 'Settings', component: () => import('../views/Settings.vue'), meta: { title: '系统设置' } },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.public && !localStorage.getItem('token')) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router
