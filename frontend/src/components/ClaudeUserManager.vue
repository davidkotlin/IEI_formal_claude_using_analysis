<template>
  <el-dialog v-model="visible" title="👥 名單管理（本組）" width="640px" @open="load">
    <el-alert
      title="改名只影響顯示；刪除會連同該用戶在本組的所有對話與訊息一起刪除，且無法復原。"
      type="info" show-icon :closable="false" style="margin-bottom: 8px"
    />
    <el-alert v-if="msg" :title="msg" :type="msgType" show-icon style="margin: 8px 0" @close="msg = ''" />

    <!-- 列表 -->
    <el-table :data="users" size="small" border max-height="360" v-loading="loading">
      <el-table-column prop="email" label="Email" min-width="220" />
      <el-table-column prop="name" label="顯示名" min-width="140">
        <template #default="{ row }">
          <el-input v-if="row._editing" v-model="row._name" size="small" />
          <span v-else>{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="department" label="部門" min-width="160">
        <template #default="{ row }">
          <el-input v-if="row._editing" v-model="row._dept" size="small" placeholder="（無）" />
          <span v-else>{{ row.department || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" align="center">
        <template #default="{ row }">
          <template v-if="row._editing">
            <el-button size="small" type="success" text @click="saveRow(row)">存</el-button>
            <el-button size="small" text @click="row._editing = false">取消</el-button>
          </template>
          <template v-else>
            <el-button size="small" text @click="startEdit(row)">編輯</el-button>
            <el-popconfirm
              title="確定刪除？將連同本組所有對話與訊息一起刪除，無法復原！"
              width="260"
              confirm-button-text="刪除"
              confirm-button-type="danger"
              @confirm="remove(row)"
            >
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
import { getUsers, renameClaudeUser, deleteClaudeUser, setClaudeUserDepartment } from '../api/index.js'

const visible = defineModel({ type: Boolean, default: false })
const emit = defineEmits(['changed'])

const users = ref([])
const loading = ref(false)
const msg = ref('')
const msgType = ref('success')

function notify(text, ok = true) {
  msg.value = text
  msgType.value = ok ? 'success' : 'error'
}

async function load() {
  loading.value = true
  try {
    const res = await getUsers()   // 已自動帶當前 group，回傳 [{uuid, name, email, department}]
    users.value = res.data.users.map((u) => ({ ...u, _editing: false, _name: u.name, _dept: u.department || '' }))
  } finally {
    loading.value = false
  }
}

function startEdit(row) { row._editing = true; row._name = row.name; row._dept = row.department || '' }

async function saveRow(row) {
  const name = (row._name || '').trim()
  const dept = (row._dept || '').trim()
  if (!name) return notify('顯示名不可為空', false)
  try {
    // 名字有變才呼叫改名
    if (name !== row.name) {
      await renameClaudeUser(row.uuid, name)
      row.name = name
    }
    // 部門有變才呼叫改部門
    if (dept !== (row.department || '')) {
      await setClaudeUserDepartment(row.uuid, dept)
      row.department = dept
    }
    row._editing = false
    notify('已更新'); emit('changed')
  } catch (e) {
    notify(e.response?.data?.error ?? '更新失敗', false)
  }
}

async function remove(row) {
  try {
    const res = await deleteClaudeUser(row.uuid)
    const d = res.data
    notify(`已刪除（對話 ${d.conv_deleted}、訊息 ${d.msg_deleted}）`)
    await load(); emit('changed')
  } catch (e) {
    notify(e.response?.data?.error ?? '刪除失敗', false)
  }
}
</script>

<style scoped>
</style>
