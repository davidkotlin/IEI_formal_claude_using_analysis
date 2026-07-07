<template>
  <el-container style="min-height: 100vh">
    <!-- 側邊欄 -->
    <el-aside width="260px" class="sidebar">
      <div class="sidebar-title">OpenAI Using Analysis</div>

      <div class="filter-section">
        <div class="filter-label">📅 日期範圍</div>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="~"
          start-placeholder="開始日期"
          end-placeholder="結束日期"
          format="YYYY/MM/DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
          @change="fetchAll"
        />
      </div>

      <div class="filter-section">
        <div class="filter-label-row">
          <span class="filter-label">👥 選擇帳號</span>
          <div>
            <el-button size="small" text @click="selectAll">全選</el-button>
            <el-button size="small" text @click="clearAll">全不選</el-button>
          </div>
        </div>
        <el-select
          v-model="selectedEmails"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          placeholder="選擇帳號"
          style="width: 100%"
        >
          <el-option v-for="u in allUsers" :key="u.email" :label="u.name || u.email" :value="u.email" />
        </el-select>
      </div>

      <el-button type="primary" plain style="width: 100%; margin-top: 12px" :loading="loading" @click="refresh">
        🔄 重新整理
      </el-button>

      <el-divider />

      <div class="filter-label">🗂️ 名單管理</div>
      <el-button style="width: 100%" @click="managerOpen = true">開啟名單管理</el-button>

      <el-divider />

      <div class="filter-label">📁 手動匯入 CSV / 名單</div>
      <el-button size="small" style="width: 100%" @click="$refs.fileInput.click()">選擇檔案（可多選）</el-button>
      <input ref="fileInput" type="file" multiple accept=".csv,.xlsx" style="display:none" @change="onImportFiles" />

      <div v-if="importFiles.length" class="file-list">
        <div class="file-list-head">
          已選 {{ importFiles.length }} 個檔案
          <el-button size="small" text @click="clearFiles">全部清空</el-button>
        </div>
        <div v-for="f in importFiles" :key="f.name" class="file-row" :class="{ bad: importBad.includes(f.name) }">
          <span class="file-name">{{ f.name }}</span>
          <el-button size="small" text type="danger" @click="removeFile(f.name)">✕</el-button>
        </div>
      </div>

      <el-alert
        v-if="importBad.length"
        type="error"
        :closable="false"
        show-icon
        style="margin-top: 8px"
        title="檔名不符規則，請改名重選"
      >
        <div class="rule-hint">
          users*.xlsx（名單）、codex*.csv（Codex）、leaderboard-YYYY-MM-DD.csv（網頁版）
        </div>
      </el-alert>

      <el-button
        type="success"
        plain
        style="width: 100%; margin-top: 8px"
        :loading="importing"
        :disabled="importFiles.length === 0 || importBad.length > 0"
        @click="doImport"
      >
        📤 匯入
      </el-button>

      <el-alert
        v-if="importResult"
        :title="importResult"
        :type="importError ? 'error' : 'success'"
        show-icon
        style="margin-top: 8px"
        @close="importResult = ''"
      />
    </el-aside>

    <!-- 主內容 -->
    <el-main class="main-content">
      <div class="page-header">
        <h2>📊 OpenAI Using Analysis</h2>
        <el-radio-group v-model="source" @change="onSourceChange">
          <el-radio-button value="codex">Codex</el-radio-button>
          <el-radio-button value="web">網頁版</el-radio-button>
        </el-radio-group>
        <span class="date-range-label">{{ dateRangeLabel }}</span>
      </div>

      <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />

      <!-- 區塊1 -->
      <OpenAiStatsCards :data="summary" :source="source" :metric-label="metricLabel" style="margin-bottom: 24px" />

      <!-- 區塊2 -->
      <OpenAiRanking
        :ranking="ranking"
        :inactive="inactive"
        :source="source"
        style="margin-bottom: 24px"
        @metric-change="onMetricChange"
        @inactive-toggle="onInactiveToggle"
        @inactive-scope-change="onInactiveScopeChange"
      />

      <!-- 區塊3 -->
      <OpenAiMatrix :matrix="matrix" :source="source" />
    </el-main>

    <OpenAiUserManager v-model="managerOpen" @changed="reloadUsers" />
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import OpenAiStatsCards from '../components/OpenAiStatsCards.vue'
import OpenAiRanking from '../components/OpenAiRanking.vue'
import OpenAiMatrix from '../components/OpenAiMatrix.vue'
import OpenAiUserManager from '../components/OpenAiUserManager.vue'
import {
  getOpenAiUsers, getOpenAiSummary, getOpenAiRanking, getOpenAiInactive, getOpenAiMatrix,
  importOpenAiData,
} from '../api/index.js'

// --- 狀態 ---
const allUsers = ref([])
const selectedEmails = ref([])
const dateRange = ref([])
const source = ref('codex')
const currentMetric = ref('codex_total')
const inactiveScope = ref('source')   // 未使用名單範圍：'source'=當前來源、'both'=兩個都沒用
const loading = ref(false)
const error = ref('')
const managerOpen = ref(false)

// --- 手動上傳 ---
const importFiles = ref([])       // File[]
const importBad = ref([])         // 不符規則的檔名
const importing = ref(false)
const importResult = ref('')
const importError = ref(false)

function classifyName(name) {
  const n = (name || '').toLowerCase()
  if (/^users.*\.xlsx?$/.test(n)) return 'roster'
  if (/^codex.*\.csv$/.test(n)) return 'codex'
  if (/^leaderboard-\d{4}-\d{2}-\d{2}\.csv$/.test(n)) return 'web'   // 精確：leaderboard-YYYY-MM-DD.csv
  return 'unknown'
}

function revalidate() {
  importBad.value = importFiles.value
    .filter((f) => classifyName(f.name) === 'unknown')
    .map((f) => f.name)
}

function onImportFiles(e) {
  const picked = Array.from(e.target.files)
  // 累加到現有清單，用檔名去重（多次開視窗選取會接在後面，不覆蓋）
  const existing = new Set(importFiles.value.map((f) => f.name))
  const merged = [...importFiles.value]
  for (const f of picked) {
    if (!existing.has(f.name)) merged.push(f)
  }
  importFiles.value = merged
  importResult.value = ''
  revalidate()
  e.target.value = ''   // 清掉 input，讓同一檔還能再觸發 change
}

function removeFile(name) {
  importFiles.value = importFiles.value.filter((f) => f.name !== name)
  revalidate()
  importResult.value = ''
}

function clearFiles() {
  importFiles.value = []
  importBad.value = []
  importResult.value = ''
}

async function doImport() {
  importing.value = true
  importResult.value = ''
  importError.value = false
  try {
    const res = await importOpenAiData(importFiles.value)
    const rows = res.data.results || []
    const ok = rows.filter((r) => !r.error).length
    importResult.value = `匯入完成：${ok}/${rows.length} 個檔案處理成功`
    importFiles.value = []
    await reloadUsers()   // 匯入可能含名單 xlsx，名單會變 → 重抓左側帳號清單
    await fetchAll()
  } catch (e) {
    importError.value = true
    const d = e.response?.data
    importResult.value = d?.bad_files ? `${d.error}：${d.bad_files.join('、')}` : (d?.error ?? '匯入失敗')
  } finally {
    importing.value = false
  }
}

const summary = ref({})
const ranking = ref([])
const inactive = ref([])
const matrix = ref({ dates: [], rows: [] })

// --- 計算屬性 ---
const dateRangeLabel = computed(() => {
  if (!dateRange.value?.length) return ''
  const [s, e] = dateRange.value
  return s === e ? s : `${s} ~ ${e}`
})

const metricLabel = computed(() => ({
  codex_total: 'Token 總計', uncached: 'Uncached', cached: 'Cached',
  output: 'Output', sessions: 'Session 數', messages: '訊息數', web_tokens: 'Tokens',
}[currentMetric.value] ?? 'Tokens'))

const queryParams = computed(() => ({
  source: source.value,
  start_date: dateRange.value?.[0] ?? '',
  end_date: dateRange.value?.[1] ?? '',
  emails: selectedEmails.value.join(','),
}))

// --- 方法 ---
async function fetchAll() {
  // 沒選帳號時 emails 送空字串，後端視為「全部帳號」
  // 所以重新整理按鈕在未選任何帳號時＝查全部，一定會有反應
  loading.value = true
  error.value = ''
  try {
    const p = queryParams.value
    const withMetric = { ...p, metric: currentMetric.value }
    // 未使用名單依 scope 決定來源：both 或當前來源
    const inactiveP = { ...p, source: inactiveScope.value === 'both' ? 'both' : source.value }
    const [sumRes, rankRes, inactRes, matRes] = await Promise.all([
      getOpenAiSummary(withMetric),
      getOpenAiRanking(withMetric),
      getOpenAiInactive(inactiveP),
      getOpenAiMatrix(withMetric),
    ])
    summary.value = sumRes.data
    ranking.value = rankRes.data.data
    inactive.value = inactRes.data.data
    matrix.value = matRes.data
  } catch (e) {
    error.value = '資料載入失敗，請確認後端服務是否正常運行。'
  } finally {
    loading.value = false
  }
}

// 只重抓未使用名單（切換 scope 或打開名單時用，不重抓其他區塊）
async function fetchInactive() {
  const p = queryParams.value
  const src = inactiveScope.value === 'both' ? 'both' : source.value
  const res = await getOpenAiInactive({ ...p, source: src })
  inactive.value = res.data.data
}

function onSourceChange() {
  currentMetric.value = source.value === 'web' ? 'web_tokens' : 'codex_total'
  fetchAll()
}

function onMetricChange(metric) {
  currentMetric.value = metric
  fetchAll()
}

async function onInactiveToggle(show) {
  if (show) await fetchInactive()
}

function onInactiveScopeChange(scope) {
  inactiveScope.value = scope
  fetchInactive()
}

function selectAll() { selectedEmails.value = allUsers.value.map((u) => u.email); fetchAll() }
function clearAll() { selectedEmails.value = [] }

async function reloadUsers() {
  const res = await getOpenAiUsers()
  allUsers.value = res.data.data
}

// 重新整理按鈕：名單與統計都刷新
async function refresh() {
  await reloadUsers()
  await fetchAll()
}

watch(selectedEmails, () => {
  if (selectedEmails.value.length === 0) {
    summary.value = {}; ranking.value = []; inactive.value = []; matrix.value = { dates: [], rows: [] }
    return
  }
  fetchAll()
}, { deep: true })

onMounted(async () => {
  await reloadUsers()
  // 不預選、不自動抓 —— 等使用者自己選帳號或按重新整理，避免日後資料量大時初次載入過慢
})
</script>

<style scoped>
.sidebar { background: #f5f7fa; padding: 24px 16px; border-right: 1px solid #e4e7ed; }
.sidebar-title { font-size: 16px; font-weight: 600; color: #303133; margin-bottom: 24px; }
.filter-section { margin-bottom: 20px; }
.filter-label { font-size: 13px; color: #606266; margin-bottom: 8px; }
.filter-label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.main-content { padding: 24px; background: #fff; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 22px; }
.date-range-label { font-size: 14px; color: #909399; margin-left: auto; }
.file-list { margin-top: 8px; }
.file-list-head { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #909399; margin-bottom: 4px; }
.file-row { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #606266; padding: 1px 0; }
.file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-row.bad .file-name { color: #f56c6c; text-decoration: line-through; }
.rule-hint { font-size: 11px; line-height: 1.5; }
</style>
