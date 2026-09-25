<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <span>告警中心</span>
          <div>
            <el-select v-model="filterType" placeholder="类型" size="small" style="width:100px;margin-right:8px" clearable>
              <el-option label="区域拥挤" value="crowd" /><el-option label="异常逗留" value="loiter" /><el-option label="摔倒" value="fall" />
            </el-select>
            <el-select v-model="filterStatus" placeholder="状态" size="small" style="width:100px;margin-right:8px" clearable>
              <el-option label="未处理" value="pending" /><el-option label="已处理" value="handled" />
            </el-select>
            <el-date-picker v-model="filterDate" type="date" placeholder="日期" size="small" style="width:140px;margin-right:8px" value-format="YYYY-MM-DD" />
            <el-button size="small" type="primary" @click="loadAlarms">查询</el-button>
          </div>
        </div>
      </template>
      <el-table :data="alarms" size="small" stripe v-loading="loading">
        <el-table-column prop="alarm_type_display" label="类型" width="90" />
        <el-table-column prop="shelf_name" label="关联货架" width="120" />
        <el-table-column prop="message" label="内容" show-overflow-tooltip />
        <el-table-column prop="level" label="级别" width="70">
          <template #default="{ row }"><el-tag :type="row.level === 'critical' ? 'danger' : 'warning'" size="small">{{ row.level === 'critical' ? '严重' : '一般' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }"><el-tag :type="row.status === 'pending' ? 'danger' : 'success'" size="small">{{ row.status === 'pending' ? '未处理' : '已处理' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" type="primary" size="small" @click="onHandle(row.id)">处理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination layout="prev, pager, next" :total="total" :page-size="20" @current-change="loadAlarms" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlarms, handleAlarm } from '../api'

const alarms = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const filterType = ref('')
const filterStatus = ref('')
const filterDate = ref('')

async function loadAlarms(page = 1) {
  loading.value = true
  const params: any = { page }
  if (filterType.value) params.type = filterType.value
  if (filterStatus.value) params.status = filterStatus.value
  if (filterDate.value) params.date = filterDate.value
  try {
    const res: any = await getAlarms(params)
    alarms.value = res.results || res
    total.value = res.count || alarms.value.length
  } finally { loading.value = false }
}

async function onHandle(id: number) {
  await handleAlarm(id)
  ElMessage.success('已标记为已处理')
  loadAlarms()
}

loadAlarms()
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
</style>
