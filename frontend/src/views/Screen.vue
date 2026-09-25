<template>
  <div class="screen" :class="{ fullscreen }">
    <div class="screen-header">
      <h1>寻觅客 · 门店运营数据大屏</h1>
      <div class="toolbar">
        <el-date-picker v-model="date" type="date" placeholder="选择日期" size="small" style="width:130px" value-format="YYYY-MM-DD" />
        <el-button size="small" type="primary" @click="fetchAll">刷新</el-button>
        <el-button size="small" @click="toggleFullscreen">{{ fullscreen ? '退出全屏' : '全屏' }}</el-button>
      </div>
    </div>
    <div class="screen-body">
      <el-row :gutter="12">
        <el-col :span="6">
          <div class="panel">
            <div class="panel-title">今日核心指标</div>
            <div class="kpi">
              <div class="kpi-item">
                <div class="kpi-val">{{ dashboard.today_enter }}</div>
                <div class="kpi-name">进店人次</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-val">{{ dashboard.today_exit }}</div>
                <div class="kpi-name">离店人次</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-val">{{ dashboard.dwell_count }}</div>
                <div class="kpi-name">驻留次数</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-val">{{ dashboard.avg_dwell }}s</div>
                <div class="kpi-name">平均停留</div>
              </div>
              <div class="kpi-item alert">
                <div class="kpi-val">{{ dashboard.pending_alarms }}</div>
                <div class="kpi-name">待处理告警</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-val">{{ dashboard.alarms_today }}</div>
                <div class="kpi-name">今日告警</div>
              </div>
            </div>
          </div>
          <div class="panel" style="margin-top:12px">
            <div class="panel-title">最新告警</div>
            <div class="alarm-list">
              <div v-for="a in dashboard.latest_alarms" :key="a.id" class="alarm-row" :class="a.level">
                <el-tag :type="a.level === 'critical' ? 'danger' : 'warning'" size="small">{{ typeName(a.alarm_type) }}</el-tag>
                <span class="msg">{{ a.message }}</span>
                <span class="time">{{ a.created_at }}</span>
              </div>
              <el-empty v-if="!dashboard.latest_alarms?.length" description="暂无告警" :image-size="60" />
            </div>
          </div>
        </el-col>
        <el-col :span="10">
          <div class="panel">
            <div class="panel-title">区域热力图（{{ date || '今日' }}）</div>
            <div ref="heatRef" class="echart"></div>
          </div>
          <div class="panel" style="margin-top:12px">
            <div class="panel-title">货架停留时长排行</div>
            <div ref="barRef" class="echart"></div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="panel">
            <div class="panel-title">客流趋势</div>
            <div ref="trendRef" class="echart"></div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDashboard, getTrafficTrend, getHeatmap, getDwellByRoi } from '../api'

const date = ref<string>('')
const fullscreen = ref(false)
const dashboard = reactive<any>({ latest_alarms: [], top_rois: [] })
const trendRef = ref<HTMLDivElement>()
const heatRef = ref<HTMLDivElement>()
const barRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let heatChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null
let timer: number

function typeName(t: string) {
  return { crowd: '区域拥挤', loiter: '异常逗留', fall: '摔倒' }[t] || t
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().then(() => fullscreen.value = true)
  } else {
    document.exitFullscreen().then(() => fullscreen.value = false)
  }
}

function initTrend(data: any) {
  if (!trendRef.value) return
  trendChart = echarts.init(trendRef.value, 'dark')
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 24 },
    xAxis: { type: 'category', data: Array.from({ length: 24 }, (_, i) => `${i}h`) },
    yAxis: { type: 'value' },
    series: [
      { name: '进店', type: 'line', smooth: true, areaStyle: { opacity: .3 }, data: data.enter },
      { name: '离店', type: 'line', smooth: true, data: data.exit },
    ],
    legend: { data: ['进店', '离店'], top: 0 },
  })
  trendChart.on('click', (params: any) => {
    const hour = params.dataIndex
    // 时段下钻：跳转时段明细（简化处理：用 route query 传参，由用户进一步查看）
    console.log('时段下钻', hour)
  })
}

function initHeat(data: any) {
  if (!heatRef.value) return
  heatChart = echarts.init(heatRef.value, 'dark')
  const xData = Array.from({ length: data.grid_w }, (_, i) => i)
  const yData = Array.from({ length: data.grid_h }, (_, i) => i)
  heatChart.setOption({
    tooltip: { position: 'top' },
    grid: { left: 40, right: 10, top: 10, bottom: 40 },
    xAxis: { type: 'category', data: xData, show: false },
    yAxis: { type: 'category', data: yData, show: false, inverse: true },
    visualMap: { min: 0, max: 100, calculable: true, orient: 'horizontal', bottom: 0, left: 'center' },
    series: [{
      name: '热力', type: 'heatmap', data: data.data,
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,.5)' } },
    }],
  })
}

function initBar(rows: any[]) {
  if (!barRef.value) return
  barChart = echarts.init(barRef.value, 'dark')
  const names = rows.map(r => r.roi__shelf_name || `货架${r.roi_id}`)
  const values = rows.map(r => +(r.total_duration || 0).toFixed(1))
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 100, right: 20, top: 10, bottom: 24 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: names, inverse: true },
    series: [{
      type: 'bar', data: values,
      itemStyle: { borderRadius: [0, 4, 4, 0], color: new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#5470c6'},{offset:1,color:'#91cc75'}]) },
    }],
  })
  barChart.on('click', (params: any) => {
    const roiId = rows[params.dataIndex]?.roi_id
    if (roiId) {
      window.open(`/#/reports?roi=${roiId}&date=${date.value || ''}`, '_blank')
    }
  })
}

async function fetchAll() {
  const params: any = {}
  if (date.value) params.date = date.value
  try {
    const [d, trend, heat, dwell] = await Promise.all([
      getDashboard(params), getTrafficTrend(params), getHeatmap(params), getDwellByRoi(params),
    ])
    Object.assign(dashboard, d)
    initTrend(trend)
    initHeat(heat)
    initBar(dwell)
  } catch (e) { /* 拦截器已提示 */ }
}

onMounted(async () => {
  await nextTick()
  fetchAll()
  timer = window.setInterval(fetchAll, 30000)
  const onResize = () => { trendChart?.resize(); heatChart?.resize(); barChart?.resize() }
  window.addEventListener('resize', onResize)
})

onUnmounted(() => { clearInterval(timer); trendChart?.dispose(); heatChart?.dispose(); barChart?.dispose() })
</script>

<style scoped>
.screen { min-height: 100vh; background: #080c1a; color: #cfd7e0; padding: 12px; }
.fullscreen { padding: 12px; }
.screen-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.screen-header h1 { font-size: 20px; color: #fff; letter-spacing: 1px; }
.toolbar { display: flex; align-items: center; gap: 8px; }
.screen-body { display: flex; flex-direction: column; gap: 12px; }
.panel { background: #0f1428; border: 1px solid #1a2140; border-radius: 8px; padding: 12px; }
.panel-title { font-size: 14px; font-weight: 600; color: #93a5be; margin-bottom: 8px; }
.echart { width: 100%; height: 240px; }
.kpi { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.kpi-item { background: #13192e; border-radius: 6px; padding: 10px; text-align: center; }
.kpi-val { font-size: 22px; font-weight: 700; color: #5aa1ff; }
.kpi-item.alert .kpi-val { color: #f56c6c; }
.kpi-name { font-size: 12px; color: #7a8ba8; margin-top: 4px; }
.alarm-list { max-height: 240px; overflow-y: auto; }
.alarm-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #1a2140; font-size: 12px; }
.alarm-row .msg { flex: 1; }
.alarm-row .time { color: #6b7a95; }
</style>
