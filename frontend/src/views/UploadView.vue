<template>
  <div class="upload-page">
    <AppHeader />
    <div class="upload-container">
      <el-card class="upload-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <el-icon :size="24"><UploadFilled /></el-icon>
            <span>上传 Excel 文件</span>
          </div>
        </template>

        <el-upload
          ref="uploadRef"
          class="upload-area"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".xlsx,.xls"
          :on-change="handleFileChange"
          :on-exceed="handleExceed"
        >
          <el-icon class="el-icon--upload" :size="64"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将 Excel 文件拖到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="upload-tip">
              仅支持 .xlsx / .xls 格式，第一列为图片，第二列为替换文本
            </div>
          </template>
        </el-upload>

        <div class="upload-actions">
          <el-button
            type="primary"
            size="large"
            :loading="uploading"
            :disabled="!selectedFile"
            @click="handleUpload"
          >
            {{ uploading ? '上传中...' : '开始处理' }}
          </el-button>
        </div>

        <el-alert
          v-if="errorMsg"
          :title="errorMsg"
          type="error"
          show-icon
          closable
          class="error-alert"
        />
      </el-card>

      <el-card class="info-card" shadow="never">
        <template #header>
          <span>📖 使用说明</span>
        </template>
        <ol class="info-list">
          <li>准备 Excel 文件，<strong>第一列</strong>放置待处理图片（PNG格式），<strong>第二列</strong>填写替换后的文本</li>
          <li>部分图片可使用透明背景，系统会自动检测并处理</li>
          <li>上传后系统将逐行处理，通过 ComfyUI 进行文字重绘</li>
          <li>处理完成后可预览对比结果并下载 Excel 文件（结果写入第三列）</li>
        </ol>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, type UploadFile, type UploadInstance, type UploadRawFile } from 'element-plus'
import { uploadExcel } from '@/api'

const router = useRouter()
const uploadRef = ref<UploadInstance>()
const selectedFile = ref<UploadRawFile | null>(null)
const uploading = ref(false)
const errorMsg = ref('')

function handleFileChange(file: UploadFile) {
  errorMsg.value = ''
  if (file.raw) {
    selectedFile.value = file.raw
  }
}

function handleExceed() {
  ElMessage.warning('只能上传一个文件，请先移除已选文件')
}

async function handleUpload() {
  if (!selectedFile.value) return

  uploading.value = true
  errorMsg.value = ''

  try {
    const result = await uploadExcel(selectedFile.value)
    ElMessage.success(`上传成功！共 ${result.totalRows} 行待处理`)
    router.push({ name: 'TaskProgress', params: { taskId: result.taskId } })
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '上传失败，请重试'
    errorMsg.value = msg
    ElMessage.error(msg)
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-page {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.upload-container {
  max-width: 720px;
  margin: 32px auto;
  padding: 0 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}

.upload-area {
  width: 100%;
}

.upload-tip {
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}

.upload-actions {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.upload-actions .el-button {
  min-width: 200px;
}

.error-alert {
  margin-top: 16px;
}

.info-card {
  border-radius: 12px;
  background-color: #fafafa;
}

.info-list {
  padding-left: 20px;
  line-height: 2;
  color: #606266;
  font-size: 14px;
}
</style>
