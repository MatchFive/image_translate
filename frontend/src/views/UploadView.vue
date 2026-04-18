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
              :on-remove="handleExcelRemove"
            >
              <el-icon class="el-icon--upload" :size="64"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                将 Excel 文件拖到此处，或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="upload-tip">
                  支持 .xlsx / .xls 格式，上传后可选择图片列和文字列
                </div>
              </template>
            </el-upload>

            <!-- 列选择区域 -->
            <div v-if="excelColumns.length > 0" class="column-select-area">
              <el-divider content-position="left">📊 列映射配置</el-divider>
              <p class="column-hint">
                检测到 <strong>{{ excelColumns.length }}</strong> 列数据，请指定各列用途：
              </p>
              <div class="column-selectors">
                <div class="selector-item">
                  <span class="selector-label">🖼️ 图片列：</span>
                  <el-select
                    v-model="selectedImageCol"
                    placeholder="选择图片所在列"
                    size="large"
                    class="selector-dropdown"
                  >
                    <el-option
                      v-for="col in excelColumns"
                      :key="col.index"
                      :label="`第 ${col.index} 列 - ${col.name}`"
                      :value="col.index"
                    />
                  </el-select>
                </div>
                <div class="selector-item">
                  <span class="selector-label">📝 文字列：</span>
                  <el-select
                    v-model="selectedTextCol"
                    placeholder="选择替换文字所在列"
                    size="large"
                    class="selector-dropdown"
                  >
                    <el-option
                      v-for="col in excelColumns"
                      :key="col.index"
                      :label="`第 ${col.index} 列 - ${col.name}`"
                      :value="col.index"
                    />
                  </el-select>
                </div>
              </div>
            </div>

            <!-- 解析中 loading -->
            <div v-if="parsingExcel" class="parse-loading">
              <el-icon class="is-loading" :size="24"><Loading /></el-icon>
              <span>正在解析 Excel 列信息...</span>
            </div>

            <div class="upload-actions">
              <el-button
                type="primary"
                size="large"
                :loading="uploading"
                :disabled="!excelFile || !selectedImageCol || !selectedTextCol"
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

      <!-- 后端选择器（通用） -->
      <el-card v-if="availableBackends.length > 0" class="backend-card" shadow="never">
        <div class="backend-select">
          <span class="backend-label">🔧 重绘引擎：</span>
          <el-radio-group v-model="selectedBackend" size="large">
            <el-radio-button
              v-for="b in availableBackends"
              :key="b.id"
              :value="b.id"
            >
              {{ b.name }}
            </el-radio-button>
          </el-radio-group>
          <span v-if="currentBackendDesc" class="backend-desc">{{ currentBackendDesc }}</span>
        </div>
      </el-card>

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
          <li><strong>Excel 模式：</strong>上传 Excel 文件，系统自动解析所有列，您可以选择哪一列是图片、哪一列是替换文本</li>
          <li><strong>手动模式：</strong>上传单张 PNG 图片 + 输入目标文字，直接处理并返回结果</li>
          <li>部分图片可使用透明背景，系统会自动检测并处理</li>
          <li>支持多种 AI 重绘后端：百练 / Nano Banana / ComfyUI</li>
          <li>本地 OCR 验证确保文字匹配，不匹配自动重试</li>
        </ol>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { ElMessage, type UploadFile, type UploadInstance, type UploadRawFile } from 'element-plus'
import { uploadExcel, uploadManual, parseExcel, getBackends, type ExcelColumn, type ImageBackend } from '@/api'

const router = useRouter()

// 模式切换
const activeMode = ref<'excel' | 'manual'>('excel')

// Excel 模式
const excelUploadRef = ref<UploadInstance>()
const excelFile = ref<UploadRawFile | null>(null)
const excelColumns = ref<ExcelColumn[]>([])
const selectedImageCol = ref<number | null>(null)
const selectedTextCol = ref<number | null>(null)
const parsingExcel = ref(false)

// 手动模式
const manualUploadRef = ref<UploadInstance>()
const manualImage = ref<UploadRawFile | null>(null)
const manualImagePreview = ref<string>('')
const targetText = ref('')

// 通用
const uploading = ref(false)
const errorMsg = ref('')

// 后端选择
const availableBackends = ref<ImageBackend[]>([])
const selectedBackend = ref<string>('')

// 加载可用后端
getBackends().then(res => {
  availableBackends.value = res.backends
  selectedBackend.value = res.default
}).catch(() => {
  // 获取失败不影响使用
})

const currentBackendDesc = computed(() => {
  const b = availableBackends.value.find(b => b.id === selectedBackend.value)
  return b?.description || ''
})

function handleExceed() {
  ElMessage.warning('只能上传一个文件，请先移除已选文件')
}

// ---- Excel ----
async function handleExcelChange(file: UploadFile) {
  errorMsg.value = ''
  if (!file.raw) return
  excelFile.value = file.raw

  // 自动解析列头
  parsingExcel.value = true
  excelColumns.value = []
  selectedImageCol.value = null
  selectedTextCol.value = null

  try {
    const result = await parseExcel(file.raw)
    excelColumns.value = result.columns
    // 默认选第1列为图片列，第2列为文字列（如果有的话）
    if (result.columns.length >= 2) {
      selectedImageCol.value = result.columns[0].index
      selectedTextCol.value = result.columns[1].index
    } else if (result.columns.length === 1) {
      selectedImageCol.value = result.columns[0].index
    }
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || 'Excel 解析失败'
    errorMsg.value = msg
  } finally {
    parsingExcel.value = false
  }
}

function handleExcelRemove() {
  excelFile.value = null
  excelColumns.value = []
  selectedImageCol.value = null
  selectedTextCol.value = null
}

async function handleExcelUpload() {
  if (!excelFile.value || !selectedImageCol.value || !selectedTextCol.value) return
  if (selectedImageCol.value === selectedTextCol.value) {
    errorMsg.value = '图片列和文字列不能是同一列'
    return
  }

  uploading.value = true
  errorMsg.value = ''

  try {
    const result = await uploadExcel(
      excelFile.value,
      selectedImageCol.value,
      selectedTextCol.value,
      selectedBackend.value
    )
    ElMessage.success(`上传成功！共 ${result.total_items} 行待处理`)
    router.push({ name: 'TaskProgress', params: { taskId: result.task_id } })
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
    const result = await uploadManual(manualImage.value, targetText.value.trim(), selectedBackend.value)
    ElMessage.success('图片已提交处理！')
    router.push({ name: 'TaskProgress', params: { taskId: result.task_id } })
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

.column-select-area {
  margin-top: 20px;
  padding: 16px;
  background: #f0f5ff;
  border-radius: 10px;
  border: 1px solid #d9e4ff;
}

.column-hint {
  margin: 8px 0 16px;
  color: #606266;
  font-size: 14px;
}

.column-selectors {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.selector-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selector-label {
  font-size: 15px;
  font-weight: 500;
  min-width: 100px;
  color: #303133;
}

.selector-dropdown {
  flex: 1;
}

.parse-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  color: #409eff;
  font-size: 14px;
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

.backend-card {
  border-radius: 12px;
  margin-top: -8px;
}

.backend-select {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.backend-label {
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
}

.backend-desc {
  color: #909399;
  font-size: 13px;
}
</style>
