<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>📊 用量排名（{{ sourceLabel }}）</span>
        <div class="header-controls">
          <el-select
            v-if="source === 'codex'"
            v-model="metric"
            size="small"
            style="width: 150px; margin-right: 12px"
            @change="$emit('metric-change', metric)"
          >
            <el-option label="🔢 Token 總計" value="codex_total" />
            <el-option label="🆕 Uncached" value="uncached" />
            <el-option label="♻️ Cached" value="cached" />
            <el-option label="📤 Output" value="output" />
            <el-option label="🗂️ Session 數" value="sessions" />
            <el-option label="💬 訊息數" value="messages" />
          </el-select>
          <el-switch v-model="showInactive" active-text="未使用者" />
        </div>
      </div>
    </template>

    <!-- 未使用者名單 -->
    <template v-if="showInactive">
      <div class="inactive-header">
        未使用者名單（共 {{ inactive.length }} 人）
        <el-input
          v-model="search"
          placeholder="搜尋 email 或姓名..."
          size="small"
          clearable
          style="width: 240px; margin-left: 12px"
        />
      </div>
      <el-row :gutter="8" style="margin-top: 12px">
        <el-col v-for="u in filteredInactive" :key="u.email" :span="8" style="margin-bottom: 6px">
          <span class="inactive-name">{{ displayName(u.name, u.email) }}</span>
        </el-col>
      </el-row>
      <el-empty v-if="filteredInactive.length === 0" description="找不到符合的人" />
    </template>

    <!-- 排名長條圖 -->
    <template v-else>
      <v-chart :option="chartOption" style="height: 380px" autoresize />
    </template>
  </el-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { abbr, full, displayName } from '../utils/format.js'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  ranking:  { type: Array, default: () => [] },
  inactive: { type: Array, default: () => [] },
  source:   { type: String, default: 'codex' },
})

const emit = defineEmits(['metric-change', 'inactive-toggle'])

const metric = ref('codex_total')
const showInactive = ref(false)
const search = ref('')

// 來源切換時把 metric 重設為該來源預設值，並通知父層重抓
watch(() => props.source, (s) => {
  metric.value = s === 'web' ? 'web_tokens' : 'codex_total'
  emit('metric-change', metric.value)
})

watch(showInactive, (v) => emit('inactive-toggle', v))

const sourceLabel = computed(() => (props.source === 'web' ? '網頁版' : 'Codex'))

const filteredInactive = computed(() => {
  const kw = search.value.trim().toLowerCase()
  if (!kw) return props.inactive
  return props.inactive.filter(
    (u) => (u.email || '').toLowerCase().includes(kw) || (u.name || '').toLowerCase().includes(kw)
  )
})

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter: (ps) => {
      const p = ps[0]
      return `${p.axisValue}<br/>${full(p.value)}`
    },
  },
  grid: { left: 60, right: 20, bottom: 80, top: 20 },
  xAxis: {
    type: 'category',
    data: props.ranking.map((r) => displayName(r.name, r.email)),
    axisLabel: { rotate: 35, fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    axisLabel: { formatter: (v) => abbr(v) },
  },
  series: [{
    type: 'bar',
    data: props.ranking.map((r) => r.value),
    label: { show: true, position: 'top', fontSize: 10, formatter: (p) => abbr(p.value) },
    itemStyle: { color: '#409eff' },
  }],
}))
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-controls { display: flex; align-items: center; }
.inactive-header { display: flex; align-items: center; font-size: 14px; color: #606266; }
.inactive-name { font-size: 13px; color: #303133; margin-right: 6px; }
.inactive-email { font-size: 11px; color: #909399; }
</style>
