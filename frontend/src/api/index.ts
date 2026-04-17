import axios from 'axios'
import type { Task, UploadResponse } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

/** Excel 列信息 */
export interface ExcelColumn {
  index: number
  name: string
}

/** Excel 解析响应 */
export interface ExcelParseResponse {
  temp_id: string
  temp_dir: string
  filename: string
  columns: ExcelColumn[]
}

/** 解析 Excel 列头 */
export async function parseExcel(file: File): Promise<ExcelParseResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<ExcelParseResponse>('/tasks/parse-excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

/** 上传 Excel 文件（指定图片列和文字列） */
export async function uploadExcel(
  file: File,
  imageCol: number,
  textCol: number
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('image_col', String(imageCol))
  formData.append('text_col', String(textCol))
  const { data } = await api.post<UploadResponse>('/tasks/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

/** 手动上传单张图片 + 目标文本 */
export async function uploadManual(
  file: File,
  targetText: string
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('target_text', targetText)
  const { data } = await api.post<UploadResponse>('/tasks/upload-manual', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

/** 获取任务详情 */
export async function getTask(taskId: string): Promise<Task> {
  const { data } = await api.get<Task>(`/tasks/${taskId}`)
  return data
}

/** 下载处理完成的 Excel / 结果图片 */
export function getDownloadUrl(taskId: string): string {
  return `/api/tasks/${taskId}/download`
}
