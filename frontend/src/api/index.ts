import axios from 'axios'
import type { Task, UploadResponse } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

/** 上传 Excel 文件 */
export async function uploadExcel(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<UploadResponse>('/tasks/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 大文件上传可能较慢
  })
  return data
}

/** 获取任务详情 */
export async function getTask(taskId: string): Promise<Task> {
  const { data } = await api.get<Task>(`/tasks/${taskId}`)
  return data
}

/** 下载处理完成的 Excel */
export function getDownloadUrl(taskId: string): string {
  return `/api/tasks/${taskId}/download`
}
