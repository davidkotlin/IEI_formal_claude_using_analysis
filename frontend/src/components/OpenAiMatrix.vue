<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>🗓️ 逐日使用矩陣（{{ sourceLabel }}）</span>
        <span class="hint">只顯示區間內有使用的人 · 空白＝當天沒用</span>
      </div>
    </template>

    <el-empty v-if="!matrix.dates?.length" description="此區間沒有使用資料" />

    <el-table
      v-else
      :data="matrix.rows"
      size="small"
      border
      :cell-class-name="cellClass"
      style="width: 100%"
    >
      <el-table-column prop="name" label="使用者" fixed min-width="150">
        <template #default="{ row }">
          <span class="u-name">{{ displayName(row.name, row.email) }}</span>
        </template>
      </el-table-column>

      <el-table-column
        v-for="(d, i) in matrix.dates"
        :key="d"
        :label="shortDate(d)"
        align="center"
        min-width="80"
      >
        <template #default="{ row }">
          <span v-if="row.cells[i] != null" class="used" :title="full(row.cells[i])">
            {{ abbr(row.cells[i]) }}
          </span>
          <span v-else class="unused">·</span>
        </template>
      </el-table-column>

      <el-table-column label="區間總計" align="right" fixed="right" min-width="100">
        <template #default="{ row }">
          <strong :title="full(row.total)">{{ abbr(row.total) }}</strong>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { abbr, full, shortDate, displayName } from '../utils/format.js'

const props = defineProps({
  matrix: { type: Object, default: () => ({ dates: [], rows: [] }) },
  source: { type: String, default: 'codex' },
})

const sourceLabel = computed(() => (props.source === 'web' ? '網頁版' : 'Codex'))

// 沒用的格子淡化底色，一眼看出誰哪幾天空著
function cellClass({ row, columnIndex }) {
  // columnIndex 0 是使用者欄，最後一欄是總計；中間才是日期
  const dateCount = props.matrix.dates?.length ?? 0
  if (columnIndex >= 1 && columnIndex <= dateCount) {
    const i = columnIndex - 1
    return row.cells[i] == null ? 'cell-empty' : 'cell-used'
  }
  return ''
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: baseline; }
.hint { font-size: 12px; color: #909399; }
.user-cell { display: flex; flex-direction: column; line-height: 1.3; }
.u-name { font-size: 13px; color: #303133; }
.u-email { font-size: 11px; color: #909399; }
.used { font-size: 12px; color: #303133; }
.unused { color: #dcdfe6; }
</style>

<style>
/* 非 scoped：el-table 的 cell class 需作用到內部 td */
.cell-empty { background: #fafafa; }
.cell-used  { background: #ecf5ff; }
</style>
