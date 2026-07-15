<template>
  <el-row :gutter="24">
    <!-- 活躍使用人數 -->
    <el-col :span="8">
      <el-card shadow="never">
        <div class="stat-label">👥 活躍使用人數</div>
        <div class="stat-value">{{ data.active_users }} / {{ data.total_users }} 人</div>
        <div class="stat-sub">{{ data.active_pct }}%</div>
      </el-card>
    </el-col>

    <!-- 對話指標（可切換：總對話數 / 平均每人對話數 / 對話來回數平均）-->
    <el-col :span="8">
      <el-card shadow="never">
        <div class="stat-label-row">
          <span>💬 對話指標</span>
          <el-select v-model="convMetric" size="small" style="width: 130px">
            <el-option label="總對話數" value="total" />
            <el-option label="平均每人對話數" value="avg" />
            <el-option label="對話來回數(平均)" value="rounds" />
          </el-select>
        </div>
        <div class="stat-value">{{ convValue }} {{ convUnit }}</div>
        <div class="stat-sub">{{ convSub }}</div>
      </el-card>
    </el-col>

    <!-- 對話時長中位數 -->
    <el-col :span="8">
      <el-card shadow="never">
        <div class="stat-label">⏱️ 每次對話平均時長</div>
        <div class="stat-value">{{ data.duration_mean }} 分鐘</div>
        <div class="stat-sub">篩選時間範圍內，每次對話首尾訊息的時間差平均值</div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    default: () => ({
      active_users: 0,
      total_users: 0,
      active_pct: 0,
      rounds: { mean: 0, median: 0, mode: 0 },
      duration_mean: 0,
      conversation_count: 0,
    }),
  },
})

const convMetric = ref('total')

const convValue = computed(() => {
  const d = props.data
  if (convMetric.value === 'total') return d.conversation_count ?? 0
  if (convMetric.value === 'avg') {
    const n = d.active_users || 0
    return n ? Math.round(((d.conversation_count ?? 0) / n) * 10) / 10 : 0
  }
  return d.rounds?.mean ?? 0   // rounds
})

const convUnit = computed(() => (convMetric.value === 'rounds' ? '次' : '場'))

const convSub = computed(() => ({
  total:  '篩選範圍內有訊息活動的總對話場數',
  avg:    '總對話數 ÷ 活躍人數',
  rounds: '每人對話來回（human 訊息）平均數',
}[convMetric.value]))
</script>

<style scoped>
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.stat-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}
.stat-sub {
  font-size: 12px;
  color: #67c23a;
}
</style>
