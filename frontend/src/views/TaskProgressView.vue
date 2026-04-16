<template>
  <div class="progress-page">
    <AppHeader />
    <div class="progress-container">
      <el-card class="progress-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>📊 处理进度</span>
            <el-tag :type="statusTagType" size="large">{{ statusLabel }}</el-tag>
          </div>
        </template>

        <!-- 总进度 -->
        <div class="overall-progress">
          <el-progress
            :percentage="overallPercentage"
            :status="progressStatus"
            :stroke-width="20"
            :text-inside="true"
          />
          <p class="progress-text">
            已处理 {{ processedRows }} / {{ totalRows }} 行
          </p>
        </div>

        <!-- 每行状态列表 -->
        <div class="row-list">
          <div
            v-for="row in rows"
            :key="row.row"
            class="row-item"
            :class="{ 'row-active': row.status === 'processing' }"
          >
            <div class="row-info">
              <el-tag
                :type="getRowTagType(row.status)"
                size="small"
                effect="dark"
                round
              >
                第 {{ row.row }} 行
              </el-tag>
              <span class="row-status-text">
                {{ getRowStatusText(row) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="actions" v-if="task?.status === 'completed'">
          <el-button type="primary" size="large" @click="goToResult">
            查看结果 🎉
          </el-button>
        </div>
        <div class="actions" v-if="task?.status === 'failed'">
          <el-button type="warning" @click="goHome">返回重试</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTask } from '@/api'
import type { Task, RowProgress, WsProgressMessage } from '@/types'
import AppHeader from '@/components/AppHeader.vue'

const router = useRouter()
const route = useRoute()
const taskId = computed(() => route.params.taskId as string)

const task = ref<Task | null>(null)
const rows = ref<RowProgress[]>([])
const processedRows = ref(0)
const totalRows = ref(0)
let ws: WebSocket | null = null

const overallPercentage = computed(() => {
  if (totalRows.value === 0) return 0
  return Math.round((processedRows.value / totalRows.value) * 100)
})

const statusTagType = computed(() => {
  if (!task.value) return 'info'
  const map: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[task.value.status] || 'info'
})

const statusLabel = computed(() => {
  if (!task.value) return '加载中...'
  const map: Record<string, string> = {
    pending: '等待处理',
    processing: '处理中',
    completed: '处理完成',
    failed: '处理失败',
  }
  return map[task.value.status] || task.value.status
})

const progressStatus = computed(() => {
  if (!task.value) return undefined
  if (task.value.status === 'completed') return 'success' as const
  if (task.value.status === 'failed') return 'exception' as const
  return undefined
})

function getRowTagType(status: string) {
  const map: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

function getRowStatusText(row: RowProgress) {
  const map: Record<string, string> = {
    pending: '等待处理',
    processing: '正在处理...',
    completed: '✅ 完成',
    failed: `❌ 失败${row.message ? ': ' + row.message : ''}`,
  }
  let text = map[row.status] || row.status
  if (row.ocrRetryCount && row.ocrRetryCount > 0 && row.status === 'processing') {
    text += ` (OCR重试第${row.ocrRetryCount}次)`
  }
  return text
}

async function loadTask() {
  try {
    task.value = await getTask(taskId.value)
    totalRows.value = task.value.totalRows
    processedRows.value = task.value.processedRows
    // 初始化行列表
    rows.value = Array.from({ length: task.value.totalRows }, (_, i) => ({
      row: i + 1,
      status: i < task.value.processedRows ? 'completed' as const : 'pending' as const,
    }))
  } catch (err: any) {
    ElMessage.error('加载任务信息失败')
  }
}

function connectWs() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${location.host}/ws/tasks/${taskId.value}`
  ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    try {
      const msg: WsProgressMessage = JSON.parse(event.data)

      if (msg.type === 'progress' && msg.rowProgress) {
        const idx = rows.value.findIndex(r => r.row === msg.rowProgress!.row)
        if (idx >= 0) {
          rows.value[idx] = msg.rowProgress
        }
        processedRows.value = msg.currentRow ?? processedRows.value
      } else if (msg.type === 'completed') {
        // 重新加载任务
        loadTask()
      } else if (msg.type === 'failed') {
        loadTask()
        ElMessage.error(msg.error || '处理失败')
      }
    } catch {
      // 忽略解析错误
    }
  }

  ws.onerror = () => {
    ElMessage.warning('WebSocket 连接断开，尝试重连...')
    setTimeout(connectWs, 3000)
  }

  ws.onclose = () => {
    // 如果任务还没完成，尝试重连
    if (task.value && task.value.status !== 'completed' && task.value.status !== 'failed') {
      setTimeout(connectWs, 3000)
    }
  }
}

function goToResult() {
  router.push({ name: 'Result', params: { taskId: taskId.value } })
}

function goHome() {
  router.push({ name: 'Upload' })
}

onMounted(() => {
  loadTask().then(() => {
    connectWs()
  })
})

onUnmounted(() => {
  ws?.close()
  ws = null
})
</script>

<style scoped>
.progress-page {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.progress-container {
  max-width: 720px;
  margin: 32px auto;
  padding: 0 24px;
}

.progress-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.overall-progress {
  margin-bottom: 24px;
}

.progress-text {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}

.row-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.row-item {
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.3s;
}

.row-item:last-child {
  border-bottom: none;
}

.row-item.row-active {
  background-color: #fdf6ec;
}

.row-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.row-status-text {
  font-size: 13px;
  color: #606266;
}

.actions {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
