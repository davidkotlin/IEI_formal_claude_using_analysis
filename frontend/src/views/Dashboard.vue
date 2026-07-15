<template>
  <el-container style="min-height: 100vh">
    <!-- 側邊欄 -->
    <el-aside width="260px" class="sidebar">
      <div class="sidebar-title">Claude Using Analysis</div>

      <div class="filter-section">
        <div class="filter-label">🏢 組別</div>
        <el-select v-model="group" style="width: 100%" @change="onGroupChange">
          <el-option :value="1" label="組別 1" />
          <el-option :value="2" label="組別 2" />
          <el-option :value="3" label="組別 3" />
        </el-select>
      </div>

      <div class="filter-section">
        <div class="filter-label">🏬 部門</div>
        <el-select
          v-model="selectedDept"
          placeholder="全部部門"
          multiple
          collapse-tags
          collapse-tags-tooltip
          clearable
          filterable
          style="width: 100%"
          @change="onDeptChange"
        >
          <el-option v-for="d in deptOptions" :key="d" :label="d" :value="d" />
        </el-select>
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
          <span class="filter-label">👥 選擇用戶</span>
          <div>
            <el-button size="small" text @click="selectAll">全選</el-button>
            <el-button size="small" text @click="clearAll">全不選</el-button>
          </div>
        </div>
        <el-select
          v-model="selectedUsers"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          :placeholder="viewAll ? '✓ 已全選（全部用戶）' : '選擇用戶'"
          style="width: 100%"
        >
          <el-option
            v-for="u in allUsers"
            :key="u.uuid"
            :label="u.name"
            :value="u.uuid"
          />
        </el-select>
      </div>

      <el-button
        type="primary"
        plain
        style="width: 100%; margin-top: 12px"
        :loading="loading"
        @click="refresh"
      >
        🔄 重新整理
      </el-button>
      <el-divider />
      <div class="filter-label">🗂️ 名單管理</div>
      <el-button
        style="width: 100%"
        @click="managerOpen = true"
      >
        👥開啟名單管理
      </el-button>

      <el-divider />

      <div class="filter-label">📁 手動匯入資料</div>
      <div class="upload-item">
        <span class="upload-label">users.json</span>
        <el-button size="small" @click="$refs.usersInput.click()">選擇檔案</el-button>
        <span class="upload-filename">{{ usersFile?.name ?? '未選擇' }}</span>
        <input ref="usersInput" type="file" accept=".json" style="display:none" @change="onUsersFile" />
      </div>
      <div class="upload-item">
        <span class="upload-label">conversations.json</span>
        <el-button size="small" @click="$refs.convInput.click()">選擇檔案</el-button>
        <span class="upload-filename">{{ convFile?.name ?? '未選擇' }}</span>
        <input ref="convInput" type="file" accept=".json" style="display:none" @change="onConvFile" />
      </div>
      <el-button
        type="success"
        plain
        style="width: 100%; margin-top: 8px"
        :loading="importing"
        :disabled="!usersFile || !convFile"
        @click="handleImport"
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
        <h2>📊 Claude Using Analysis</h2>
        <span class="date-range-label">{{ dateRangeLabel }}</span>
      </div>

      <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />

      <!-- KPI 卡片 -->
      <StatsCards :data="summary" style="margin-bottom: 24px" />

      <!-- 用戶排名 -->
      <UserRanking
        :ranking="ranking"
        :inactive="inactive"
        style="margin-bottom: 24px"
        @metric-change="onMetricChange"
        @inactive-toggle="onInactiveToggle"
      />

      <!-- 時段分析 -->
      <HourlyChart :data="hourly" />
    </el-main>

    <ClaudeUserManager v-model="managerOpen" @changed="onManagerChanged" />
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import StatsCards from '../components/StatsCards.vue'
import UserRanking from '../components/UserRanking.vue'
import HourlyChart from '../components/HourlyChart.vue'
import ClaudeUserManager from '../components/ClaudeUserManager.vue'
import { getUsers, getInactiveUsers, getSummary, getRanking, getHourly, importData, importDepartments, setClaudeGroup } from '../api/index.js'

// --- 狀態 ---
const group       = ref(1)          // 當前組別 1/2/3
const managerOpen = ref(false)      // 名單管理對話框
const viewAll     = ref(false)      // 全選模式：selectedUsers 空但代表「查全部」
const selectedDept = ref([])        // 部門篩選（多選；空=全部部門）
const allUsers    = ref([])
const selectedUsers = ref([])
const dateRange   = ref([])
const loading     = ref(false)
const error       = ref('')

const usersFile   = ref(null)
const convFile    = ref(null)
const importing   = ref(false)
const importResult = ref('')
const importError  = ref(false)

const deptFile      = ref(null)
const deptImporting = ref(false)
const deptResult    = ref('')
const deptError     = ref(false)

const summary  = ref({})
const ranking  = ref([])
const inactive = ref([])
const hourly   = ref([])
const currentMetric = ref('messages')

// --- 計算屬性 ---
const dateRangeLabel = computed(() => {
  if (!dateRange.value?.length) return ''
  const [s, e] = dateRange.value
  return s === e ? s : `${s} ~ ${e}`
})

const queryParams = computed(() => ({
  start_date: dateRange.value?.[0] ?? '',
  end_date:   dateRange.value?.[1] ?? '',
  // 全選模式：UI 雖裝滿（給藍勾），但送出時送空 = 後端查全部（URL 短，不塞 uuid）
  users:      viewAll.value ? '' : selectedUsers.value.join(','),
}))

// 當前組的部門清單（去重、排序，供部門下拉）
const deptOptions = computed(() => {
  const set = new Set(allUsers.value.map((u) => u.department).filter(Boolean))
  return [...set].sort()
})

// --- 方法 ---
async function fetchAll() {
  if (selectedUsers.value.length === 0 && !viewAll.value) {
    summary.value = {}
    ranking.value = []
    inactive.value = []
    hourly.value = []
    return
  }
  // 日期守衛：未選日期範圍前不查詢，給明確提示（與後端強制日期一致）
  if (!dateRange.value || !dateRange.value[0] || !dateRange.value[1]) {
    error.value = '請先選擇日期範圍（開始日期與結束日期），再查詢。'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const params = queryParams.value
    const [summaryRes, rankingRes, inactiveRes, hourlyRes] = await Promise.all([
      getSummary(params),
      getRanking({ ...params, metric: currentMetric.value }),
      getInactiveUsers(params),
      getHourly(params),
    ])
    summary.value  = summaryRes.data
    ranking.value  = rankingRes.data.data
    inactive.value = inactiveRes.data.inactive
    hourly.value   = hourlyRes.data.data
  } catch (e) {
    // 後端若因缺日期回 400，顯示後端訊息；其餘顯示通用失敗
    const msg = e.response?.data?.error
    error.value = msg || '資料載入失敗，請確認後端服務是否正常運行。'
  } finally {
    loading.value = false
  }
}

// 切換組別：更新 api 的 group、清空選擇與統計、重抓該組名單
async function onGroupChange(g) {
  setClaudeGroup(g)
  viewAll.value = false
  selectedDept.value = []
  selectedUsers.value = []
  summary.value = {}; ranking.value = []; inactive.value = []; hourly.value = []
  await reloadUsers()
}

// 選部門（多選）：把 selectedUsers 設成所選部門的所有人聯集；清空=不篩（回到手動選）
function onDeptChange(depts) {
  viewAll.value = false
  if (!depts || depts.length === 0) {
    selectedUsers.value = []
    return
  }
  const set = new Set(depts)
  selectedUsers.value = allUsers.value
    .filter((u) => set.has(u.department))
    .map((u) => u.uuid)
  // watch 會偵測 selectedUsers 變化並自動查詢
}

function hasDates() {
  return dateRange.value && dateRange.value[0] && dateRange.value[1]
}

async function onMetricChange(metric) {
  currentMetric.value = metric
  if ((selectedUsers.value.length === 0 && !viewAll.value) || !hasDates()) return
  const res = await getRanking({ ...queryParams.value, metric })
  ranking.value = res.data.data
}

function selectAll() {
  viewAll.value = true                                    // 送出時 users 會轉空（URL 短）
  selectedUsers.value = allUsers.value.map((u) => u.uuid) // UI 裝滿 → 每個人顯示藍勾
  // 不呼叫 fetchAll()，交給 watch 觸發（watch 會因 viewAll 而查全部）
}

function clearAll() {
  viewAll.value = false
  selectedUsers.value = []
  summary.value = {}; ranking.value = []; inactive.value = []; hourly.value = []
}

function onUsersFile(e) {
  usersFile.value = e.target.files[0]
}

function onConvFile(e) {
  convFile.value = e.target.files[0]
}

async function handleImport() {
  importing.value = true
  importResult.value = ''
  importError.value = false
  try {
    const res = await importData(usersFile.value, convFile.value)
    const d = res.data
    importResult.value = `完成！新增 ${d.conv_inserted} 筆，略過重複 ${d.conv_skipped_dup} 筆、週末 ${d.conv_skipped_weekend} 筆、空對話 ${d.conv_skipped_empty} 筆。`
    usersFile.value = null
    convFile.value = null
    await reloadUsers()   // 上傳可能含新的 users.json，名單會變 → 重抓用戶清單
    await fetchAll()
  } catch (e) {
    importError.value = true
    importResult.value = e.response?.data?.error ?? '匯入失敗'
  } finally {
    importing.value = false
  }
}

function onDeptFile(e) {
  deptFile.value = e.target.files[0] ?? null
}

async function handleDeptImport() {
  deptImporting.value = true
  deptResult.value = ''
  deptError.value = false
  try {
    const res = await importDepartments(deptFile.value)
    const d = res.data
    const bs = d.by_source || {}
    deptResult.value = `部門更新完成！共更新 ${d.updated} 人（Excel ${bs.excel ?? 0}、上海 ${bs['上海'] ?? 0}、美國 ${bs['美國'] ?? 0}、百視美 ${bs['百視美'] ?? 0}），略過 ${d.skipped} 人。`
    deptFile.value = null
    await reloadUsers()
  } catch (e) {
    deptError.value = true
    deptResult.value = e.response?.data?.error ?? '部門匯入失敗'
  } finally {
    deptImporting.value = false
  }
}

async function onInactiveToggle(show) {
  if (show) {
    if ((selectedUsers.value.length === 0 && !viewAll.value) || !hasDates()) {
      error.value = '請先選擇日期範圍與用戶，再查看未使用者。'
      return
    }
    const res = await getInactiveUsers(queryParams.value)
    inactive.value = res.data.inactive
  }
}

// --- 監聽用戶篩選變化 ---
watch(selectedUsers, () => {
  // 全選模式只在「全部人都還選中」時維持；若手動取消了某人（不再全滿）就離開全選模式
  if (viewAll.value && selectedUsers.value.length !== allUsers.value.length) {
    viewAll.value = false
  }
  if (selectedUsers.value.length === 0 && !viewAll.value) {
    summary.value = {}
    ranking.value = []
    inactive.value = []
    hourly.value = []
    return
  }
  fetchAll()
}, { deep: true })

// --- 初始化 ---
// 名單管理（改名/刪除）後：重抓名單，並移除已選中但已被刪除的 uuid
async function onManagerChanged() {
  await reloadUsers()
  const valid = new Set(allUsers.value.map((u) => u.uuid))
  selectedUsers.value = selectedUsers.value.filter((uid) => valid.has(uid))
}

async function reloadUsers() {
  const res = await getUsers()
  allUsers.value = res.data.users   // [{uuid, name, email}]
}

// 重新整理按鈕：名單與統計都刷新
async function refresh() {
  await reloadUsers()
  await fetchAll()
}

onMounted(async () => {
  setClaudeGroup(group.value)   // 確保 api 的 group 與畫面一致
  await reloadUsers()
  // 不預選、不自動抓 —— 等使用者自己選用戶或按重新整理
})
</script>

<style scoped>
.sidebar {
  background: #f5f7fa;
  padding: 24px 16px;
  border-right: 1px solid #e4e7ed;
}
.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 24px;
}
.filter-section {
  margin-bottom: 20px;
}
.filter-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}
.main-content {
  padding: 24px;
  background: #fff;
}
.page-header {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 24px;
}
.page-header h2 {
  margin: 0;
  font-size: 22px;
}
.date-range-label {
  font-size: 14px;
  color: #909399;
}
.filter-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.upload-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.upload-label {
  font-size: 12px;
  color: #606266;
  min-width: 60px;
}
.upload-filename {
  font-size: 11px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 80px;
}
</style>
