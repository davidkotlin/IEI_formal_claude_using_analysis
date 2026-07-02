<template>
  <div>
    <el-radio-group v-model="view" style="padding: 12px 24px">
      <el-radio-button label="claude">Claude</el-radio-button>
      <el-radio-button label="openai">OpenAI</el-radio-button>
    </el-radio-group>
    <Dashboard v-if="view === 'claude'" />
    <OpenAiDashboard v-else />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import Dashboard from './views/Dashboard.vue'
import OpenAiDashboard from './views/OpenAiDashboard.vue'
const view = ref('claude')
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #fff;
}
</style>
