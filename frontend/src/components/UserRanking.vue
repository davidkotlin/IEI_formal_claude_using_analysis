<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>📊 用戶詳細數據排名</span>
        <div class="header-controls">
          <el-select v-model="metric" size="small" style="width: 140px; margin-right: 12px" @change="$emit('metric-change', metric)">
            <el-option label="💬 訊息總數" value="messages" />
            <el-option label="📁 對話數" value="conversations" />
            <el-option label="⏱️ 使用時長" value="duration" />
            <el-option label="🛠️ 調用工具數" value="tools" />
          </el-select>
          <el-switch
            v-model="showInactive"
            active-text="未使用者"
            @change="$emit('inactive-toggle', showInactive)"
          />
        </div>
      </div>
    </template>

    <!-- 未使用者名單 -->
    <template v-if="showInactive">
      <div class="inactive-header">
        <span>未使用者名單（共 {{ inactive.length }} 人）</span>
        <div class="inactive-actions">
          <el-input
            v-model="search"
            placeholder="搜尋姓名..."
            size="small"
            clearable
            style="width: 180px"
          />
          <el-button size="small" @click="copyAllEmails" :disabled="filteredInactive.length === 0">
            📋 複製全部 Email（{{ filteredInactive.length }}）
          </el-button>
        </div>
      </div>

      <div class="chip-wrap">
        <el-tooltip
          v-for="u in filteredInactive"
          :key="u.uuid"
          placement="top"
          :show-after="150"
        >
          <template #content>
            <div class="tip">
              <div class="tip-title">{{ u.name }}</div>
              <div class="tip-sub">全時段累積用量</div>
              <div class="tip-row"><span>對話數</span><b>{{ u.lifetime.conversations }}</b></div>
              <div class="tip-row"><span>總時長</span><b>{{ u.lifetime.duration_min }} 分</b></div>
              <div class="tip-row"><span>工具數</span><b>{{ u.lifetime.tool_use }}</b></div>
              <div v-if="isDeadAccount(u)" class="tip-dead">⚠️ 全時段從未使用</div>
            </div>
          </template>
          <span
            class="chip"
            :class="{ 'chip-dead': isDeadAccount(u) }"
            @click="copyEmail(u.email)"
            :title="`點擊複製 ${u.email}`"
          >
            {{ u.name }}
          </span>
        </el-tooltip>
      </div>

      <el-empty v-if="filteredInactive.length === 0" description="找不到符合的姓名" />
    </template>

    <!-- 排名長條圖 -->
    <template v-else>
      <v-chart :option="chartOption" style="height: 360px" autoresize />
    </template>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  ranking: { type: Array, default: () => [] },
  inactive: { type: Array, default: () => [] },   // [{uuid, name, email, lifetime}]
})

defineEmits(['metric-change', 'inactive-toggle'])

const metric = ref('messages')
const showInactive = ref(false)
const search = ref('')

const filteredInactive = computed(() =>
  search.value
    ? props.inactive.filter((u) => (u.name || '').toLowerCase().includes(search.value.toLowerCase()))
    : props.inactive
)

function isDeadAccount(u) {
  const lt = u.lifetime || {}
  return !lt.conversations && !lt.duration_min && !lt.tool_use
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

const yLabel = computed(() => ({
  messages: '訊息總數',
  conversations: '對話數（場）',
  duration: '平均對話時長（分鐘）',
  tools: '工具調用數',
}[metric.value]))

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: props.ranking.map((r) => r.name),
    axisLabel: { rotate: 30, fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    name: yLabel.value,
  },
  series: [{
    type: 'bar',
    data: props.ranking.map((r) => r.value),
    label: { show: true, position: 'top', fontSize: 10 },
    itemStyle: { color: '#409eff' },
  }],
}))
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-controls {
  display: flex;
  align-items: center;
}
.inactive-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}
.inactive-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.chip-wrap {
  display: grid;
  grid-template-rows: repeat(10, auto);  /* 每欄固定 10 個 */
  grid-auto-flow: column;                /* 填滿一欄(10個)才往右一欄 */
  grid-auto-columns: max-content;
  gap: 8px 12px;
  justify-content: start;
}
.chip {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 4px 12px;
  font-size: 13px;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.chip:hover {
  background: #e0ecff;
  border-color: #93c5fd;
  color: #1d4ed8;
}
.chip-dead {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}
.chip-dead:hover {
  background: #fee2e2;
  border-color: #f87171;
  color: #991b1b;
}
.tip {
  min-width: 150px;
  line-height: 1.6;
}
.tip-title {
  font-weight: 600;
  font-size: 13px;
}
.tip-sub {
  font-size: 11px;
  opacity: 0.7;
  margin-bottom: 4px;
}
.tip-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
}
.tip-dead {
  margin-top: 4px;
  font-size: 11px;
  color: #fca5a5;
}
</style>
