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

    <!-- 對話來回數 -->
    <el-col :span="8">
      <el-card shadow="never">
        <div class="stat-label-row">
          <span>💬 對話來回數</span>
          <el-select v-model="roundsMode" size="small" style="width: 90px">
            <el-option label="平均數" value="mean" />
            <el-option label="中位數" value="median" />
            <el-option label="眾數" value="mode" />
          </el-select>
        </div>
        <div class="stat-value">{{ roundsValue }} 次</div>
        <div class="stat-sub">{{ roundsLabel }}</div>
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
    }),
  },
})

const roundsMode = ref('mean')

const roundsValue = computed(() => props.data.rounds?.[roundsMode.value] ?? 0)

const roundsLabel = computed(() => ({
  mean:   '每人對話來回平均數',
  median: '每人對話來回中位數',
  mode:   '最常見的對話來回數',
}[roundsMode.value]))
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
