<template>
  <el-card shadow="never">
    <template #header>📈 時段分析（00:00 - 23:00）</template>
    <v-chart :option="chartOption" style="height: 360px" autoresize />
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const hours = Array.from({ length: 24 }, (_, i) => i)

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { type: 'scroll', bottom: 0 },
  xAxis: {
    type: 'category',
    data: hours,
    axisLabel: { formatter: (v) => `${v}:00` },
  },
  yAxis: {
    type: 'value',
    name: '對話觸發次數',
    minInterval: 1,
  },
  series: props.data.map((user) => ({
    name: user.name,
    type: 'line',
    data: user.hours,
    symbol: 'circle',
    symbolSize: 6,
  })),
}))
</script>
