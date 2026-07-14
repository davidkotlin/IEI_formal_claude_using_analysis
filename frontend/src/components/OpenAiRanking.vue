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
        <span>未使用者名單（共 {{ inactive.length }} 人）</span>
        <div class="inactive-actions">
          <el-select v-model="inactiveScope" size="small" style="width: 130px" @change="onScopeChange">
            <el-option :label="`只看${sourceLabel}`" value="source" />
            <el-option label="兩個都沒用" value="both" />
          </el-select>
          <el-input
            v-model="search"
            placeholder="搜尋 email 或姓名..."
            size="small"
            clearable
            style="width: 200px"
          />
          <el-button size="small" @click="copyAllEmails" :disabled="filteredInactive.length === 0">
            📋 複製全部 Email（{{ filteredInactive.length }}）
          </el-button>
        </div>
      </div>

      <div class="chip-wrap">
        <el-tooltip
          v-for="u in filteredInactive"
          :key="u.email"
          placement="top"
          :show-after="150"
        >
          <template #content>
            <div class="tip">
              <div class="tip-title">{{ displayName(u.name, u.email) }}</div>
              <div class="tip-sub">全時段累積 Token</div>
              <div class="tip-row"><span>Codex</span><b>{{ full(u.lifetime.codex) }}</b></div>
              <div class="tip-row"><span>網頁版</span><b>{{ full(u.lifetime.web) }}</b></div>
              <div v-if="isDeadAccount(u)" class="tip-dead">⚠️ 全時段從未使用</div>
            </div>
          </template>
          <span
            class="chip"
            :class="{ 'chip-dead': isDeadAccount(u) }"
            @click="copyEmail(u.email)"
            :title="`點擊複製 ${u.email}`"
          >
            {{ displayName(u.name, u.email) }}
          </span>
        </el-tooltip>
      </div>

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
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { abbr, full, displayName } from '../utils/format.js'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  ranking:  { type: Array, default: () => [] },
  inactive: { type: Array, default: () => [] },   // [{email, name, lifetime:{codex,web}}]
  source:   { type: String, default: 'codex' },
})

const emit = defineEmits(['metric-change', 'inactive-toggle', 'inactive-scope-change'])

const metric = ref('codex_total')
const showInactive = ref(false)
const search = ref('')
const inactiveScope = ref('source')   // 'source'=只看當前來源、'both'=兩個都沒用

// 來源切換時把 metric 重設為該來源預設值，並通知父層重抓
watch(() => props.source, (s) => {
  metric.value = s === 'web' ? 'web_tokens' : 'codex_total'
  emit('metric-change', metric.value)
  if (showInactive.value && inactiveScope.value === 'source') {
    emit('inactive-scope-change', 'source')
  }
})

watch(showInactive, (v) => emit('inactive-toggle', v))

function onScopeChange(v) {
  emit('inactive-scope-change', v)
}

const sourceLabel = computed(() => (props.source === 'web' ? '網頁版' : 'Codex'))

const filteredInactive = computed(() => {
  const kw = search.value.trim().toLowerCase()
  if (!kw) return props.inactive
  return props.inactive.filter(
    (u) => (u.email || '').toLowerCase().includes(kw) || (u.name || '').toLowerCase().includes(kw)
  )
})

function isDeadAccount(u) {
  const lt = u.lifetime || {}
  return !lt.codex && !lt.web   // codex 與 web 全時段都 0 = 死號
}

async function copyEmail(email) {
  try {
    await navigator.clipboard.writeText(email)
    ElMessage.success(`已複製：${email}`)
  } catch {
    ElMessage.error('複製失敗')
  }
}

async function copyAllEmails() {
  const emails = filteredInactive.value.map((u) => u.email).filter(Boolean).join('; ')
  if (!emails) return
  try {
    await navigator.clipboard.writeText(emails)
    ElMessage.success(`已複製 ${filteredInactive.value.length} 個 Email`)
  } catch {
    ElMessage.error('複製失敗')
  }
}

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
.inactive-header {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 14px; color: #606266; margin-bottom: 12px;
}
.inactive-actions { display: flex; align-items: center; gap: 8px; }
.chip-wrap {
  display: grid;
  grid-template-rows: repeat(10, auto);
  grid-auto-flow: column;
  grid-auto-columns: max-content;
  gap: 8px 12px;
  justify-content: start;
}
.chip {
  display: inline-flex; align-items: center; width: fit-content;
  padding: 4px 12px; font-size: 13px; color: #475569;
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 999px;
  cursor: pointer; transition: all 0.15s; user-select: none;
}
.chip:hover { background: #e0ecff; border-color: #93c5fd; color: #1d4ed8; }
.chip-dead { background: #fef2f2; border-color: #fecaca; color: #b91c1c; }
.chip-dead:hover { background: #fee2e2; border-color: #f87171; color: #991b1b; }
.tip { min-width: 150px; line-height: 1.6; }
.tip-title { font-weight: 600; font-size: 13px; }
.tip-sub { font-size: 11px; opacity: 0.7; margin-bottom: 4px; }
.tip-row { display: flex; justify-content: space-between; gap: 16px; font-size: 12px; }
.tip-dead { margin-top: 4px; font-size: 11px; color: #fca5a5; }
</style>
