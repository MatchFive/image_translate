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
  total_items: number
  completed_items: number
  failed_items: number
  status: TaskStatus
  progress: number
  created_at: string
  updated_at: string
  error_message?: string
  items?: TaskItemInfo[]
}

/** 任务子项信息 */
export interface TaskItemInfo {
  id: string
  row_index: number
  target_text: string
  status: string
  retry_count: number
  ocr_result?: string
  ocr_match_score?: number
  error_message?: string
  original_image_url?: string
  result_image_url?: string
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
  task_id: string
  message: string
  total_items: number
}
