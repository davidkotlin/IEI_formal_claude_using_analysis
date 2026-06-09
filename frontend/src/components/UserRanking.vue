<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>📊 用戶詳細數據排名</span>
        <div class="header-controls">
          <el-select v-model="metric" size="small" style="width: 140px; margin-right: 12px" @change="$emit('metric-change', metric)">
            <el-option label="💬 訊息總數" value="messages" />
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
        未使用者名單（共 {{ inactive.length }} 人）
        <el-input
          v-model="search"
          placeholder="搜尋姓名..."
          size="small"
          clearable
          style="width: 200px; margin-left: 12px"
        />
      </div>
      <el-row :gutter="8" style="margin-top: 12px">
        <el-col
          v-for="name in filteredInactive"
          :key="name"
          :span="6"
          style="margin-bottom: 6px"
        >
          <span class="inactive-name">{{ name }}</span>
        </el-col>
      </el-row>
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
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  ranking: { type: Array, default: () => [] },
  inactive: { type: Array, default: () => [] },
})

defineEmits(['metric-change', 'inactive-toggle'])

const metric = ref('messages')
const showInactive = ref(false)
const search = ref('')

const filteredInactive = computed(() =>
  search.value
    ? props.inactive.filter((n) => n.toLowerCase().includes(search.value.toLowerCase()))
    : props.inactive
)

const yLabel = computed(() => ({
  messages: '訊息總數',
  duration: '時長中位數（分鐘）',
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
  font-size: 14px;
  color: #606266;
}
.inactive-name {
  font-size: 13px;
  color: #303133;
}
</style>
