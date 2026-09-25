<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <span>驻留记录</span>
          <div>
            <el-date-picker v-model="date" type="date" placeholder="日期" size="small" style="width:140px;margin-right:8px" value-format="YYYY-MM-DD" />
            <el-button size="small" type="primary" @click="onSearch">查询</el-button>
          </div>
        </div>
      </template>
      <el-table :data="records" size="small" v-loading="loading" stripe>
        <el-table-column prop="track_id" label="顾客ID" width="90" />
        <el-table-column prop="shelf_name" label="货架" />
        <el-table-column prop="enter_time" label="进入时间" width="160" />
        <el-table-column prop="leave_time" label="离开时间" width="160" />
        <el-table-column prop="duration" label="停留时长" width="100">
          <template #default="{ row }">{{ row.duration ? row.duration + ' 秒' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }"><el-tag :type="row.is_active ? 'primary' : 'success'" size="small">{{ row.is_active ? '进行中' : '已结束' }}</el-tag></template>
        </el-table-column>
      </el-table>
      <el-pagination layout="prev, pager, next" :total="total" :page-size="20" @current-change="loadPage" style="margin-top:16px" />
    </el-card>

    <el-card shadow="never" style="margin-top:16px">
      <template #header>
        <div class="header">
          <span>轨迹回放</span>
          <div>
            <el-select v-model="trackId" placeholder="选择顾客" size="small" style="width:160px;margin-right:8px" filterable>
              <el-option v-for="t in tracks" :key="t.track_id" :label="`#${t.track_id} 最后出现 ${t.last_time} 驻留${t.dwell_count}次`" :value="t.track_id" />
            </el-select>
            <el-button size="small" type="primary" @click="playTrajectory">回放</el-button>
          </div>
        </div>
      </template>
      <div ref="trajRef" class="echart"></div>
      <el-empty v-if="!trajectoryPoints.length" description="选择顾客后点击回放，展示该顾客在店内的移动轨迹" :image-size="80" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { getDwellRecords, getTracks, getTrajectory } from '../api'

const date = ref('')
const records = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const trackId = ref<number | null>(null)
const tracks = ref<any[]>([])
const trajectoryPoints = ref<any[]>([])
const trajRef = ref<HTMLDivElement>()
let trajChart: echarts.ECharts | null = null

async function loadPage(page = 1) {
  loading.value = true
  const params: any = { page }
  if (date.value) params.date = date.value
  try {
    const res: any = await getDwellRecords(params)
    records.value = res.results || res
    total.value = res.count || records.value.length
  } finally { loading.value = false }
}

function onSearch() { loadPage(1) }

async function loadTracks() {
  const res: any = await getTracks({ date: date.value })
  tracks.value = res
}

async function playTrajectory() {
  if (!trackId.value) return
  const res: any = await getTrajectory({ track_id: trackId.value, date: date.value })
  trajectoryPoints.value = res.points || []
  if (!trajRef.value) return
  trajChart = echarts.init(trajRef.value)
  trajChart.setOption({
    tooltip: {},
    xAxis: { type: 'value', min: 0, max: 1, show: false },
    yAxis: { type: 'value', min: 0, max: 1, inverse: true, show: false },
    series: [{
      type: 'line', data: trajectoryPoints.value.map((p: any) => [p[0], p[1]]),
      lineStyle: { color: '#5470c6', width: 2 },
      itemStyle: { color: '#5470c6' },
      symbolSize: 6,
    }],
  })
}

onMounted(() => { loadPage(); loadTracks() })
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
.echart { width: 100%; height: 320px; }
</style>
