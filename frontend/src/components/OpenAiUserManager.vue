<template>
  <el-dialog v-model="visible" title="👥 名單管理" width="640px" @open="load">
    <!-- 新增 -->
    <div class="add-row">
      <el-input v-model="newEmail" placeholder="email（必填）" size="small" style="width: 220px" />
      <el-input v-model="newName" placeholder="姓名" size="small" style="width: 160px" />
      <el-button type="primary" size="small" :loading="adding" @click="add">新增</el-button>
    </div>
    <el-alert v-if="msg" :title="msg" :type="msgType" show-icon style="margin: 8px 0" @close="msg = ''" />

    <!-- 列表 -->
    <el-table :data="users" size="small" border max-height="360" v-loading="loading">
      <el-table-column prop="email" label="Email" min-width="200" />
      <el-table-column prop="name" label="姓名" min-width="140">
        <template #default="{ row }">
          <el-input v-if="row._editing" v-model="row._name" size="small" />
          <span v-else>{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="department" label="部門" min-width="200">
        <template #default="{ row }">
          <el-input
            v-if="row._editing"
            v-model="row._department"
            size="small"
            placeholder="完整路徑，如 醫療事業中心/產品設計處/系統設計部"
          />
          <span v-else>{{ row.department || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="啟用" width="80" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.active === 1"
            @change="(v) => toggleActive(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <template v-if="row._editing">
            <el-button size="small" type="success" text @click="saveRow(row)">存</el-button>
            <el-button size="small" text @click="row._editing = false">取消</el-button>
          </template>
          <template v-else>
            <el-button size="small" text @click="startEdit(row)">編輯</el-button>
            <el-popconfirm title="確定刪除？用量紀錄保留" @confirm="remove(row)">
              <template #reference>
                <el-button size="small" type="danger" text>刪除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import {
  getOpenAiUsers, createOpenAiUser, updateOpenAiUser, deleteOpenAiUser,
} from '../api/index.js'

const visible = defineModel({ type: Boolean, default: false })
const emit = defineEmits(['changed'])

const users = ref([])
const loading = ref(false)
const adding = ref(false)
const newEmail = ref('')
const newName = ref('')
const msg = ref('')
const msgType = ref('success')

function notify(text, ok = true) {
  msg.value = text
  msgType.value = ok ? 'success' : 'error'
}

async function load() {
  loading.value = true
  try {
    const res = await getOpenAiUsers()
    users.value = res.data.data.map((u) => ({ ...u, _editing: false, _name: u.name, _department: u.department || '' }))
  } finally {
    loading.value = false
  }
}

async function add() {
  if (!newEmail.value.trim()) return notify('email 必填', false)
  adding.value = true
  try {
    await createOpenAiUser({ email: newEmail.value.trim(), name: newName.value.trim() })
    newEmail.value = ''; newName.value = ''
    notify('已新增')
    await load(); emit('changed')
  } catch (e) {
    notify(e.response?.data?.error ?? '新增失敗', false)
  } finally {
    adding.value = false
  }
}

function startEdit(row) { row._editing = true; row._name = row.name; row._department = row.department || '' }

async function saveRow(row) {
  try {
    const dept = (row._department || '').trim()
    await updateOpenAiUser(row.email, { name: row._name, department: dept })
    row.name = row._name
    row.department = dept
    row._editing = false
    notify('已更新'); emit('changed')
  } catch (e) {
    notify(e.response?.data?.error ?? '更新失敗', false)
  }
}

async function toggleActive(row, val) {
  try {
    await updateOpenAiUser(row.email, { active: val ? 1 : 0 })
    row.active = val ? 1 : 0
    notify('已更新'); emit('changed')
  } catch (e) {
    notify(e.response?.data?.error ?? '更新失敗', false)
  }
}

async function remove(row) {
  try {
    await deleteOpenAiUser(row.email)
    notify('已刪除'); await load(); emit('changed')
  } catch (e) {
    notify(e.response?.data?.error ?? '刪除失敗', false)
  }
}
</script>

<style scoped>
.add-row { display: flex; gap: 8px; align-items: center; margin-bottom: 4px; }
</style>
