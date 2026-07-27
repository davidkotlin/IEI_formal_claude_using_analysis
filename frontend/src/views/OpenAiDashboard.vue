<template>
  <el-container style="min-height: 100vh">
    <!-- 側邊欄 -->
    <el-aside width="260px" class="sidebar">
      <div class="sidebar-title">OpenAI Using Analysis</div>

      <div class="filter-section">
        <div class="filter-label">🏬 部門</div>
        <el-tree-select
          v-model="selectedDeptPath"
          :data="deptTree"
          placeholder="全部部門"
          clearable
          filterable
          check-strictly
          :render-after-expand="false"
          node-key="path"
          :props="{ label: 'label', children: 'children' }"
          style="width: 100%"
          @change="onDeptChange"
        />
      </div>

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
      <el-button style="width: 100%" @click="managerOpen = true">👥開啟名單管理</el-button>

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

      <el-divider />

      <div class="filter-label">🏢 匯入部門（employee Excel）</div>
      <div class="upload-item">
        <span class="upload-label">員工名冊 .xlsx</span>
        <el-button size="small" @click="$refs.deptInput.click()">選擇檔案</el-button>
        <span class="upload-filename">{{ deptFile?.name ?? '未選擇' }}</span>
        <input ref="deptInput" type="file" accept=".xlsx,.xlsm" style="display:none" @change="onDeptFile" />
      </div>
      <el-button
        type="primary"
        plain
        style="width: 100%; margin-top: 8px"
        :loading="deptImporting"
        :disabled="!deptFile"
        @click="handleDeptImport"
      >
        🏢 匯入部門
      </el-button>
      <el-alert
        v-if="deptResult"
        :title="deptResult"
        :type="deptError ? 'error' : 'success'"
        show-icon
        style="margin-top: 8px"
        @close="deptResult = ''"
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

      <!-- 部門訂閱費用（全部 active × 25 USD，前端 computed 連動部門樹） -->
      <DepartmentCost :data="deptCost" style="margin-bottom: 24px" />

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
import DepartmentCost from '../components/DepartmentCost.vue'
import {
  getOpenAiUsers, getOpenAiSummary, getOpenAiRanking, getOpenAiInactive, getOpenAiMatrix,
  importOpenAiData, importOpenAiDepartments,
} from '../api/index.js'

// --- 狀態 ---
const allUsers = ref([])
const selectedEmails = ref([])
const selectedDeptPath = ref('')      // 部門篩選（樹選取的完整路徑，空=全部部門）
const dateRange = ref([])
const source = ref('codex')
const currentMetric = ref('codex_total')
const inactiveScope = ref('source')   // 未使用名單範圍：'source'=當前來源、'both'=兩個都沒用
const loading = ref(false)
const error = ref('')
const managerOpen = ref(false)
const SEAT_PRICE = 25                  // 每座月費 USD（部門費用用）

// --- 部門 Excel 匯入 ---
const deptFile = ref(null)
const deptImporting = ref(false)
const deptResult = ref('')
const deptError = ref(false)

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

// 名單裡出現過的部門（去重、排序）—— 建樹用；含 inactive，方便篩選時也能選到停用帳號
const deptOptions = computed(() => {
  const set = new Set(allUsers.value.map((u) => u.department).filter(Boolean))
  return [...set].sort()
})

// 把完整部門字串（A/B/C）依 / 拆成樹。node value=從根到此的完整路徑（避開同名陷阱），label=該層名稱。
const deptTree = computed(() => {
  const roots = []
  const index = new Map()
  for (const full of deptOptions.value) {
    const segs = full.split('/')
    let prefix = ''
    let siblings = roots
    for (const seg of segs) {
      prefix = prefix ? `${prefix}/${seg}` : seg
      let node = index.get(prefix)
      if (!node) {
        node = { path: prefix, label: seg, value: prefix, children: [] }
        index.set(prefix, node)
        siblings.push(node)
      }
      siblings = node.children
    }
  }
  const prune = (nodes) => nodes.forEach((n) => {
    if (n.children.length === 0) delete n.children
    else prune(n.children)
  })
  prune(roots)
  return roots
})

// 部門費用（跟部門樹選取連動，解讀A）：
//  - 沒選 → 各「第一層」排行
//  - 選了任一節點 → 回溯其第一層，顯示該第一層底下各「第二層」排行（不管選多深都是第二層）
//  - 單層部門 → 顯示其自身那一層
// OpenAI 無組別，母體＝全部 active 帳號（× 25 USD）。
const deptCost = computed(() => {
  const path = selectedDeptPath.value
  let depth, scopeTop
  if (!path) {
    depth = 1; scopeTop = null
  } else {
    scopeTop = path.split('/')[0]
    depth = 2
  }

  const counts = {}
  for (const u of allUsers.value) {
    if (Number(u.active) !== 1) continue          // 只計 active
    const dept = (u.department || '').trim()
    if (!dept) continue                           // 沒部門不計入
    const segs = dept.split('/')
    if (scopeTop && segs[0] !== scopeTop) continue
    const key = segs.slice(0, depth).join('/')
    counts[key] = (counts[key] || 0) + 1
  }

  return Object.entries(counts)
    .map(([full, n]) => ({
      department: full.split('/').slice(-1)[0],   // 只顯示最後一段名稱
      fullPath: full,
      headcount: n,
      cost: n * SEAT_PRICE,
    }))
    .sort((a, b) => b.cost - a.cost)
})

// --- 方法 ---
function hasDates() {
  return dateRange.value && dateRange.value[0] && dateRange.value[1]
}

async function fetchAll() {
  // 日期守衛：未選日期範圍前不查詢（與後端強制日期一致）
  if (!hasDates()) {
    error.value = '請先選擇日期範圍（開始日期與結束日期），再查詢。'
    return
  }
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
    error.value = e.response?.data?.error || '資料載入失敗，請確認後端服務是否正常運行。'
  } finally {
    loading.value = false
  }
}

// 只重抓未使用名單（切換 scope 或打開名單時用，不重抓其他區塊）
async function fetchInactive() {
  if (!hasDates()) {
    error.value = '請先選擇日期範圍，再查看未使用者。'
    return
  }
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

// 選部門（樹）：選某節點 → 篩出 department 以該完整路徑開頭的所有帳號（選父帶子）。
// 用字首比對，且以 path 或 path/ 開頭，避免「醫療事業中心」誤中「醫療事業中心X」。
// watch(selectedEmails) 會偵測變化並自動查詢。
function onDeptChange(path) {
  if (!path) {                       // 清空 = 不篩
    selectedEmails.value = []
    return
  }
  selectedEmails.value = allUsers.value
    .filter((u) => u.department && (u.department === path || u.department.startsWith(path + '/')))
    .map((u) => u.email)
}

function onDeptFile(e) {
  deptFile.value = e.target.files[0] ?? null
}

async function handleDeptImport() {
  deptImporting.value = true
  deptResult.value = ''
  deptError.value = false
  try {
    const res = await importOpenAiDepartments(deptFile.value)
    const d = res.data
    const bs = d.by_source || {}
    deptResult.value = `部門更新完成！共更新 ${d.updated} 人（Excel ${bs.excel ?? 0}、上海 ${bs['上海'] ?? 0}），略過 ${d.skipped} 人。`
    deptFile.value = null
    await reloadUsers()   // 部門值變了 → 重抓名單，樹與費用才會更新
  } catch (e) {
    deptError.value = true
    deptResult.value = e.response?.data?.error ?? '部門匯入失敗'
  } finally {
    deptImporting.value = false
  }
}

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
.upload-item { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.upload-label { font-size: 12px; color: #606266; min-width: 60px; }
.upload-filename { font-size: 11px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80px; }
</style>
