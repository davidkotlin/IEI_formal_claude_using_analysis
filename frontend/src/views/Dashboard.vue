<template>
  <el-container style="min-height: 100vh">
    <!-- 側邊欄 -->
    <el-aside width="260px" class="sidebar">
      <div class="sidebar-title">Claude Using Analysis</div>

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
          placeholder="選擇用戶"
          style="width: 100%"
        >
          <el-option
            v-for="u in allUsers"
            :key="u"
            :label="u"
            :value="u"
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
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import StatsCards from '../components/StatsCards.vue'
import UserRanking from '../components/UserRanking.vue'
import HourlyChart from '../components/HourlyChart.vue'
import { getUsers, getInactiveUsers, getSummary, getRanking, getHourly, importData } from '../api/index.js'

// --- 狀態 ---
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
  users:      selectedUsers.value.join(','),
}))

// --- 方法 ---
async function fetchAll() {
  if (selectedUsers.value.length === 0) {
    summary.value = {}
    ranking.value = []
    inactive.value = []
    hourly.value = []
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
    error.value = '資料載入失敗，請確認後端服務是否正常運行。'
  } finally {
    loading.value = false
  }
}

async function onMetricChange(metric) {
  currentMetric.value = metric
  const res = await getRanking({ ...queryParams.value, metric })
  ranking.value = res.data.data
}

function selectAll() {
  selectedUsers.value = [...allUsers.value]
  fetchAll()
}

function clearAll() {
  selectedUsers.value = []
  fetchAll()
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

async function onInactiveToggle(show) {
  if (show) {
    const res = await getInactiveUsers(queryParams.value)
    inactive.value = res.data.inactive
  }
}

// --- 監聽用戶篩選變化 ---
watch(selectedUsers, () => {
  if (selectedUsers.value.length === 0) {
    summary.value = {}
    ranking.value = []
    inactive.value = []
    hourly.value = []
    return
  }
  fetchAll()
}, { deep: true })

// --- 初始化 ---
async function reloadUsers() {
  const res = await getUsers()
  allUsers.value = res.data.users
}

// 重新整理按鈕：名單與統計都刷新
async function refresh() {
  await reloadUsers()
  await fetchAll()
}

onMounted(async () => {
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
