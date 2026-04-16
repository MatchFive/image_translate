<template>
  <div class="app-header">
    <div class="header-content">
      <h1 class="title">🖼️ Image Translate</h1>
      <span class="subtitle">图片文字智能替换工具</span>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.app-header {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  color: #fff;
  padding: 24px 0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.title {
  font-size: 24px;
  font-weight: 700;
}

.subtitle {
  font-size: 14px;
  opacity: 0.85;
}
</style>
