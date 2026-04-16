/** 任务状态 */
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed'

/** 单行处理状态 */
export interface RowProgress {
  row: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  ocrRetryCount?: number
  message?: string
}

/** 任务信息 */
export interface Task {
  id: string
  filename: string
  totalRows: number
  processedRows: number
  status: TaskStatus
  createdAt: string
  completedAt?: string
  error?: string
}

/** WebSocket 进度消息 */
export interface WsProgressMessage {
  type: 'progress' | 'completed' | 'failed'
  taskId: string
  currentRow?: number
  totalRows?: number
  rowProgress?: RowProgress
  status?: TaskStatus
  error?: string
}

/** 任务来源 */
export type TaskSource = 'excel' | 'manual'

/** 上传响应 */
export interface UploadResponse {
  taskId: string
  filename: string
  totalRows: number
}
