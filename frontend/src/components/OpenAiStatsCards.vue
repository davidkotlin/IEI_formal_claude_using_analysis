<template>
  <el-row :gutter="24">
    <!-- 活躍使用人數 -->
    <el-col :span="12">
      <el-card shadow="never">
        <div class="stat-label">👥 使用人數（{{ sourceLabel }}）</div>
        <div class="stat-value">{{ data.active_users ?? 0 }} / {{ data.total_users ?? 0 }} 人</div>
        <div class="stat-sub">{{ data.active_pct ?? 0 }}% 的人在此區間內有使用</div>
      </el-card>
    </el-col>

    <!-- token 集中趨勢 -->
    <el-col :span="12">
      <el-card shadow="never">
        <div class="stat-label-row">
          <span>🔢 每人用量（{{ metricLabel }}）</span>
          <el-select v-model="mode" size="small" style="width: 90px">
            <el-option label="平均數" value="mean" />
            <el-option label="中位數" value="median" />
          </el-select>
        </div>
        <div class="stat-value">{{ tokenDisplay }}</div>
        <div class="stat-sub">{{ modeLabel }}（僅計有使用的人）</div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, computed } from 'vue'
import { abbr, full } from '../utils/format.js'

const props = defineProps({
  data:   { type: Object, default: () => ({ active_users: 0, total_users: 0, active_pct: 0, token: { mean: 0, median: 0 } }) },
  source: { type: String, default: 'codex' },
  metricLabel: { type: String, default: 'Tokens' },
})

const mode = ref('mean')

const sourceLabel = computed(() => (props.source === 'web' ? '網頁版' : 'Codex'))
const tokenValue  = computed(() => props.data.token?.[mode.value] ?? 0)
const tokenDisplay = computed(() => `${abbr(tokenValue.value)}`)
const modeLabel = computed(() => (mode.value === 'mean' ? `平均 ${full(tokenValue.value)}` : `中位 ${full(tokenValue.value)}`))
</script>

<style scoped>
.stat-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.stat-label-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #909399; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 500; color: #303133; margin-bottom: 4px; }
.stat-sub { font-size: 12px; color: #67c23a; }
</style>
