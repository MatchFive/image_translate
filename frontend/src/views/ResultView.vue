<template>
  <div class="result-page">
    <AppHeader />
    <div class="result-container">
      <el-card class="result-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>✅ 处理结果</span>
            <el-button type="primary" @click="handleDownload">
              <el-icon><Download /></el-icon>
              下载 Excel
            </el-button>
          </div>
        </template>

        <el-descriptions :column="2" border class="task-info">
          <el-descriptions-item label="文件名">{{ task?.filename }}</el-descriptions-item>
          <el-descriptions-item label="总行数">{{ task?.totalRows }}</el-descriptions-item>
          <el-descriptions-item label="处理行数">{{ task?.processedRows }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ task?.completedAt || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 预览对比区域 -->
        <div class="preview-section" v-if="previewRows.length > 0">
          <h3 class="section-title">🔍 预览对比</h3>
          <div class="preview-grid">
            <div
              v-for="item in previewRows"
              :key="item.row"
              class="preview-item"
            >
              <div class="preview-label">第 {{ item.row }} 行</div>
              <div class="preview-images">
                <div class="preview-box">
                  <span class="preview-tag">原图</span>
                  <el-image
                    :src="item.originalUrl"
                    fit="contain"
                    class="preview-img"
                  >
                    <template #error>
                      <div class="image-placeholder">加载失败</div>
                    </template>
                  </el-image>
                </div>
                <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                <div class="preview-box">
                  <span class="preview-tag">处理后</span>
                  <el-image
                    :src="item.resultUrl"
                    fit="contain"
                    class="preview-img"
                  >
                    <template #error>
                      <div class="image-placeholder">加载失败</div>
                    </template>
                  </el-image>
                </div>
              </div>
              <div class="preview-text">
                <span>目标文本: {{ item.targetText }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="actions">
          <el-button @click="goHome">继续上传</el-button>
          <el-button type="primary" @click="handleDownload">
            <el-icon><Download /></el-icon>
            下载结果
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, ArrowRight } from '@element-plus/icons-vue'
import { getTask, getDownloadUrl } from '@/api'
import type { Task } from '@/types'
import AppHeader from '@/components/AppHeader.vue'

const router = useRouter()
const route = useRoute()
const taskId = computed(() => route.params.taskId as string)

const task = ref<Task | null>(null)

interface PreviewItem {
  row: number
  originalUrl: string
  resultUrl: string
  targetText: string
}

const previewRows = ref<PreviewItem[]>([])

async function loadTask() {
  try {
    task.value = await getTask(taskId.value)
    // 生成预览数据（API 需要提供图片预览接口）
    // TODO: 从后端获取每行的原图/结果图URL和目标文本
  } catch {
    ElMessage.error('加载任务信息失败')
  }
}

function handleDownload() {
  if (!task.value) return
  const link = document.createElement('a')
  link.href = getDownloadUrl(taskId.value)
  link.download = `result_${task.value.filename}`
  link.click()
}

function goHome() {
  router.push({ name: 'Upload' })
}

onMounted(() => {
  loadTask()
})
</script>

<style scoped>
.result-page {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.result-container {
  max-width: 960px;
  margin: 32px auto;
  padding: 0 24px;
}

.result-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.task-info {
  margin-bottom: 24px;
}

.preview-section {
  margin-top: 24px;
}

.section-title {
  font-size: 16px;
  margin-bottom: 16px;
  color: #303133;
}

.preview-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.preview-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
}

.preview-label {
  font-weight: 600;
  margin-bottom: 12px;
  color: #409eff;
}

.preview-images {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.preview-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.preview-tag {
  font-size: 12px;
  color: #909399;
}

.preview-img {
  width: 100%;
  max-height: 200px;
  border: 1px solid #eee;
  border-radius: 4px;
  background-color: #fafafa;
}

.arrow-icon {
  color: #c0c4cc;
  font-size: 20px;
}

.image-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100px;
  color: #c0c4cc;
}

.preview-text {
  font-size: 13px;
  color: #606266;
  text-align: center;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}
</style>
