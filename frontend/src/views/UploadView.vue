<template>
  <div class="upload-page">
    <AppHeader />
    <div class="upload-container">

      <!-- 模式切换 Tabs -->
      <el-tabs v-model="activeMode" class="mode-tabs" stretch>
        <!-- ========== Excel 批量模式 ========== -->
        <el-tab-pane label="📄 Excel 批量上传" name="excel">
          <el-card class="upload-card" shadow="hover">
            <el-upload
              ref="excelUploadRef"
              class="upload-area"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".xlsx,.xls"
              :on-change="handleExcelChange"
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
                :disabled="!excelFile"
                @click="handleExcelUpload"
              >
                {{ uploading ? '上传中...' : '开始处理' }}
              </el-button>
            </div>
          </el-card>
        </el-tab-pane>

        <!-- ========== 手动单张模式 ========== -->
        <el-tab-pane label="🖼️ 手动上传" name="manual">
          <el-card class="upload-card" shadow="hover">
            <el-upload
              ref="manualUploadRef"
              class="upload-area"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".png"
              :on-change="handleManualImageChange"
              :on-exceed="handleExceed"
            >
              <el-icon class="el-icon--upload" :size="64"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                将 PNG 图片拖到此处，或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="upload-tip">
                  支持 PNG 格式图片，支持透明背景
                </div>
              </template>
            </el-upload>

            <!-- 图片预览 -->
            <div v-if="manualImagePreview" class="image-preview">
              <el-image
                :src="manualImagePreview"
                fit="contain"
                class="preview-img"
              />
            </div>

            <!-- 目标文本输入 -->
            <div class="target-text-input">
              <el-input
                v-model="targetText"
                type="textarea"
                :rows="3"
                placeholder="请输入需要替换的目标文字"
                maxlength="500"
                show-word-limit
                size="large"
              />
            </div>

            <div class="upload-actions">
              <el-button
                type="primary"
                size="large"
                :loading="uploading"
                :disabled="!manualImage || !targetText.trim()"
                @click="handleManualUpload"
              >
                {{ uploading ? '处理中...' : '开始替换' }}
              </el-button>
            </div>
          </el-card>
        </el-tab-pane>
      </el-tabs>

      <!-- 错误提示 -->
      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        closable
        class="error-alert"
        @close="errorMsg = ''"
      />

      <!-- 使用说明 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <span>📖 使用说明</span>
        </template>
        <ol class="info-list">
          <li><strong>Excel 模式：</strong>上传 Excel 文件，第一列放图片（PNG），第二列填写替换文本，结果写入第三列</li>
          <li><strong>手动模式：</strong>上传单张 PNG 图片 + 输入目标文字，直接处理并返回结果</li>
          <li>部分图片可使用透明背景，系统会自动检测并处理</li>
          <li>通过 ComfyUI 进行文字重绘，本地 OCR 验证确保文字匹配</li>
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
import { uploadExcel, uploadManual } from '@/api'

const router = useRouter()

// 模式切换
const activeMode = ref<'excel' | 'manual'>('excel')

// Excel 模式
const excelUploadRef = ref<UploadInstance>()
const excelFile = ref<UploadRawFile | null>(null)

// 手动模式
const manualUploadRef = ref<UploadInstance>()
const manualImage = ref<UploadRawFile | null>(null)
const manualImagePreview = ref<string>('')
const targetText = ref('')

// 通用
const uploading = ref(false)
const errorMsg = ref('')

function handleExceed() {
  ElMessage.warning('只能上传一个文件，请先移除已选文件')
}

// ---- Excel ----
function handleExcelChange(file: UploadFile) {
  errorMsg.value = ''
  if (file.raw) {
    excelFile.value = file.raw
  }
}

async function handleExcelUpload() {
  if (!excelFile.value) return
  uploading.value = true
  errorMsg.value = ''

  try {
    const result = await uploadExcel(excelFile.value)
    ElMessage.success(`上传成功！共 ${result.totalRows} 行待处理`)
    router.push({ name: 'TaskProgress', params: { taskId: result.taskId } })
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '上传失败，请重试'
    errorMsg.value = msg
  } finally {
    uploading.value = false
  }
}

// ---- 手动 ----
function handleManualImageChange(file: UploadFile) {
  errorMsg.value = ''
  if (file.raw) {
    manualImage.value = file.raw
    // 生成预览
    if (manualImagePreview.value) {
      URL.revokeObjectURL(manualImagePreview.value)
    }
    manualImagePreview.value = URL.createObjectURL(file.raw)
  }
}

async function handleManualUpload() {
  if (!manualImage.value || !targetText.value.trim()) return
  uploading.value = true
  errorMsg.value = ''

  try {
    const result = await uploadManual(manualImage.value, targetText.value.trim())
    ElMessage.success('图片已提交处理！')
    router.push({ name: 'TaskProgress', params: { taskId: result.taskId } })
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '提交失败，请重试'
    errorMsg.value = msg
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

.mode-tabs {
  background: #fff;
  border-radius: 12px;
  padding: 16px 16px 0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.upload-card {
  border: none;
  box-shadow: none;
}

.upload-area {
  width: 100%;
}

.upload-tip {
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}

.image-preview {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.preview-img {
  max-width: 300px;
  max-height: 200px;
  border: 1px solid #eee;
  border-radius: 8px;
  background-color: #fafafa;
}

.target-text-input {
  margin-top: 16px;
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
  margin-top: 0;
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
