import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Upload',
    component: () => import('@/views/UploadView.vue'),
    meta: { title: '上传文件' },
  },
  {
    path: '/task/:taskId',
    name: 'TaskProgress',
    component: () => import('@/views/TaskProgressView.vue'),
    meta: { title: '处理进度' },
  },
  {
    path: '/result/:taskId',
    name: 'Result',
    component: () => import('@/views/ResultView.vue'),
    meta: { title: '处理结果' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || '图片文字替换'} - Image Translate`
})

export default router
