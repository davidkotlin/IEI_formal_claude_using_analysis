<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>🏢 部門訂閱費用（每座 25 USD／月）</span>
        <span class="total">合計 {{ totalHeadcount }} 人 · {{ totalCost }} USD</span>
      </div>
    </template>

    <v-chart v-if="data.length" :option="chartOption" :style="{ height: chartHeight }" autoresize />
    <el-empty v-else description="此組尚無部門資料" />
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  data: { type: Array, default: () => [] },   // [{department, headcount, cost}]
})

const totalHeadcount = computed(() => props.data.reduce((s, d) => s + d.headcount, 0))
const totalCost = computed(() => props.data.reduce((s, d) => s + d.cost, 0))

// 橫條：部門多時自動長高
const chartHeight = computed(() => `${Math.max(240, props.data.length * 44)}px`)

const chartOption = computed(() => {
  // ECharts 橫條 Y 軸由下往上，所以反轉讓費用最高的在最上面
  const rows = [...props.data].sort((a, b) => a.cost - b.cost)
  return {
    grid: { left: 8, right: 90, top: 10, bottom: 10, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const d = props.data.find((x) => x.department === p[0].name)
        return `${p[0].name}<br/>${d.headcount} 人 · <b>${d.cost} USD</b>`
      },
    },
    xAxis: { type: 'value', name: 'USD' },
    yAxis: {
      type: 'category',
      data: rows.map((d) => d.department),
      axisLabel: { interval: 0 },
    },
    series: [{
      type: 'bar',
      data: rows.map((d) => d.cost),
      barWidth: '55%',
      itemStyle: { color: '#409eff', borderRadius: [0, 4, 4, 0] },
      label: {
        show: true,
        position: 'right',
        formatter: (p) => {
          const d = rows[p.dataIndex]
          return `${d.headcount} 人 · ${d.cost} USD`
        },
        color: '#475569',
      },
    }],
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.total {
  font-size: 13px;
  color: #909399;
}
</style>
