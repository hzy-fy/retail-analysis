<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <span>货架报表</span>
          <div>
            <el-select v-model="roiId" placeholder="选择货架" size="small" style="width:160px;margin-right:8px" filterable>
              <el-option v-for="r in rois" :key="r.id" :label="r.shelf_name" :value="r.id" />
            </el-select>
            <el-date-picker v-model="date" type="date" placeholder="日期" size="small" style="width:140px;margin-right:8px" value-format="YYYY-MM-DD" />
            <el-button size="small" type="primary" @click="loadDetail">查询</el-button>
          </div>
        </div>
      </template>
      <el-row :gutter="16" v-if="detail.roi_id">
        <el-col :span="4" v-for="k in statKeys" :key="k.key">
          <div class="stat-card">
            <div class="num">{{ detail[k.key] }}</div>
            <div class="label">{{ k.label }}</div>
          </div>
        </el-col>
      </el-row>
      <div ref="hourRef" class="echart" v-if="detail.roi_id"></div>
      <el-empty v-else description="选择货架和日期，查看该货架的顾客驻留指标" :image-size="80" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useRoute } from 'vue-router'
import { getRois, getRoiDetail } from '../api'

const rois = ref<any[]>([])
const roiId = ref<number | null>(null)
const date = ref('')
const detail = ref<any>({})
const hourRef = ref<HTMLDivElement>()
let hourChart: echarts.ECharts | null = null

const statKeys = [
  { key: 'count', label: '驻留人次' },
  { key: 'avg_duration', label: '平均停留(秒)' },
  { key: 'total_duration', label: '总停留(秒)' },
  { key: 'max_duration', label: '最长停留(秒)' },
]

async function loadRois() {
  const r: any = await getRois()
  rois.value = r.results || r
}

async function loadDetail() {
  if (!roiId.value) return
  const params: any = {}
  if (date.value) params.date = date.value
  const res: any = await getRoiDetail(roiId.value, params)
  detail.value = res
  await nextTick()
  if (!hourRef.value) return
  hourChart = echarts.init(hourRef.value)
  hourChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 24 },
    xAxis: { type: 'category', data: Array.from({ length: 24 }, (_, i) => `${i}h`) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: res.hourly || [], itemStyle: { borderRadius: [4, 4, 0, 0] } }],
  })
}

onMounted(async () => {
  await loadRois()
  const route = useRoute()
  if (route.query.roi) roiId.value = Number(route.query.roi)
  if (route.query.date) date.value = String(route.query.date)
  if (roiId.value) loadDetail()
})
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
.stat-card { background: var(--brand-50); border: 1px solid var(--border-1); border-radius: var(--radius-md); padding: 14px; text-align: center; }
.num { font-size: 22px; font-weight: 700; color: var(--brand-600); }
.label { font-size: 12px; color: var(--text-3); margin-top: 4px; }
.echart { width: 100%; height: 280px; margin-top: 16px; }
</style>
