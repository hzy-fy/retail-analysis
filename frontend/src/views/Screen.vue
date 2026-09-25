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
      <!-- 左侧：四个区域 2×2 平分 -->
      <div class="left-grid">
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
        <div class="panel">
          <div class="panel-title">客流趋势</div>
          <div ref="trendRef" class="echart"></div>
        </div>
        <div class="panel">
          <div class="panel-title">
            区域热力图（{{ date || '今日' }}）
            <span class="panel-sub" v-if="heatMeta.total">采样 {{ heatMeta.total }} 点 · 峰值 {{ heatMeta.max }}</span>
          </div>
          <div class="chart-box">
            <div ref="heatRef" class="echart"></div>
            <div v-if="!heatMeta.total" class="chart-empty">暂无轨迹数据<br/>启动分析后将自动累积</div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-title">货架停留时长排行</div>
          <div ref="barRef" class="echart"></div>
        </div>
      </div>
      <!-- 右侧：告警独占一列，占满全高 -->
      <div class="panel alarm-panel">
        <div class="panel-title">最新告警</div>
        <div class="alarm-list">
          <div v-for="a in dashboard.latest_alarms" :key="a.id" class="alarm-row" :class="a.level">
            <el-tag :type="a.level === 'critical' ? 'danger' : 'warning'" size="small">{{ typeName(a.alarm_type) }}</el-tag>
            <span class="msg">{{ a.message }}</span>
            <span class="time">{{ a.created_at }}</span>
          </div>
          <el-empty v-if="!dashboard.latest_alarms?.length" description="暂无告警" :image-size="80" />
        </div>
      </div>
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
const heatMeta = reactive({ total: 0, max: 0 })
const trendRef = ref<HTMLDivElement>()
const heatRef = ref<HTMLDivElement>()
const barRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let heatChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null
let timer: number
let resizeObserver: ResizeObserver | null = null

/* 浅色主题坐标轴统一样式 */
const AXIS_LABEL = { color: '#5b6b7d', fontSize: 11 }
const SPLIT_LINE = { lineStyle: { color: '#ecf1f7' } }
const AXIS_LINE = { lineStyle: { color: '#d4dee9' } }

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

function renderTrend(data: any) {
  if (!trendRef.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['进店', '离店'], top: 0, textStyle: { color: '#5b6b7d' } },
    grid: { left: 42, right: 16, top: 34, bottom: 26 },
    xAxis: { type: 'category', boundaryGap: false, data: Array.from({ length: 24 }, (_, i) => `${i}h`),
      axisLabel: AXIS_LABEL, axisLine: AXIS_LINE },
    yAxis: { type: 'value', axisLabel: AXIS_LABEL, splitLine: SPLIT_LINE },
    series: [
      { name: '进店', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5,
        itemStyle: { color: '#3b82c4' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,196,.28)' }, { offset: 1, color: 'rgba(59,130,196,.02)' }]) },
        data: data.enter },
      { name: '离店', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5,
        itemStyle: { color: '#e0a030' },
        data: data.exit },
    ],
  }, { notMerge: true })
  trendChart.off('click')
  trendChart.on('click', (params: any) => {
    const hour = params.dataIndex
    // 时段下钻
    console.log('时段下钻', hour)
  })
}

function renderHeat(data: any) {
  if (!heatRef.value) return
  if (!heatChart) heatChart = echarts.init(heatRef.value)
  heatMeta.total = data.total_points || 0
  heatMeta.max = data.max || 0
  const xData = Array.from({ length: data.grid_w }, (_, i) => i)
  const yData = Array.from({ length: data.grid_h }, (_, i) => i)
  // 峰值取后端真实值，至少为 1 避免色阶失效
  const vmax = Math.max(data.max || 0, 1)
  heatChart.setOption({
    tooltip: {
      position: 'top',
      formatter: (p: any) => `位置 (${p.value[0]}, ${p.value[1]})<br/>热度：${p.value[2]}`,
    },
    grid: { left: 8, right: 8, top: 8, bottom: 38, containLabel: false },
    xAxis: { type: 'category', data: xData, show: false, splitLine: { show: false } },
    yAxis: { type: 'category', data: yData, show: false, inverse: true, splitLine: { show: false } },
    visualMap: { min: 0, max: vmax, calculable: true, orient: 'horizontal', bottom: 0, left: 'center',
      itemWidth: 10, itemHeight: 110, precision: 0,
      textStyle: { color: '#5b6b7d', fontSize: 11 },
      inRange: { color: ['#edf4fb', '#a9cdea', '#4f93cd', '#1d5a96', '#0d3a66'] } },
    series: [{
      name: '热力', type: 'heatmap', data: data.data,
      progressive: 1000,
      itemStyle: { borderWidth: 0 },
      emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(47,111,174,.45)' } },
    }],
  }, { notMerge: true })
}

function renderBar(rows: any[]) {
  if (!barRef.value) return
  if (!barChart) barChart = echarts.init(barRef.value)
  const names = rows.map(r => r.roi__shelf_name || `货架${r.roi_id}`)
  const values = rows.map(r => +(r.total_duration || 0).toFixed(1))
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 90, right: 24, top: 10, bottom: 26 },
    xAxis: { type: 'value', axisLabel: AXIS_LABEL, splitLine: SPLIT_LINE },
    yAxis: { type: 'category', data: names, inverse: true,
      axisLabel: { ...AXIS_LABEL, width: 82, overflow: 'truncate' }, axisLine: AXIS_LINE },
    series: [{
      type: 'bar', data: values, barMaxWidth: 18,
      itemStyle: { borderRadius: [0, 6, 6, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#9dc1e2' }, { offset: 1, color: '#2f6fae' }]) },
    }],
  }, { notMerge: true })
  barChart.off('click')
  barChart.on('click', (params: any) => {
    const roiId = rows[params.dataIndex]?.roi_id
    if (roiId) {
      window.open(`/reports?roi=${roiId}&date=${date.value || ''}`, '_blank')
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
    await nextTick()
    renderTrend(trend)
    renderHeat(heat)
    renderBar(dwell)
  } catch (e) { /* 拦截器已提示 */ }
}

onMounted(async () => {
  await nextTick()
  fetchAll()
  timer = window.setInterval(fetchAll, 30000)
  // 容器尺寸变化（含全屏、侧栏切换）时重绘图表
  resizeObserver = new ResizeObserver(() => {
    trendChart?.resize()
    heatChart?.resize()
    barChart?.resize()
  })
  if (trendRef.value) resizeObserver.observe(trendRef.value)
  if (heatRef.value) resizeObserver.observe(heatRef.value)
  if (barRef.value) resizeObserver.observe(barRef.value)
})

onUnmounted(() => {
  clearInterval(timer)
  resizeObserver?.disconnect()
  trendChart?.dispose(); heatChart?.dispose(); barChart?.dispose()
})
</script>

<style scoped>
/* 高度闭合：扣除顶栏 60px 与主区上下 padding 36px */
.screen {
  height: calc(100vh - 96px);
  display: flex; flex-direction: column;
  background: var(--blue-gray-100);
  color: var(--text-1);
}
.screen-header { flex: none; display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.screen-header h1 { font-size: 19px; font-weight: 700; color: var(--text-1); letter-spacing: .5px; }
.toolbar { display: flex; align-items: center; gap: 8px; }

/* 主体：左 flex:1（2×2 等分），右告警列固定 300px 占满全高 */
.screen-body { flex: 1; min-height: 0; display: flex; gap: 12px; }
.left-grid {
  flex: 1; min-width: 0; min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 12px;
}

/* 面板：白底卡片，内部 flex 列让图表填满 */
.panel {
  display: flex; flex-direction: column; min-height: 0; min-width: 0;
  background: var(--surface);
  border: 1px solid var(--border-1);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 14px 16px;
  overflow: hidden;
}
.panel-title { flex: none; font-size: 14px; font-weight: 650; color: var(--text-1); margin-bottom: 10px;
  padding-left: 8px; border-left: 3px solid var(--brand-500); line-height: 14px;
  display: flex; align-items: center; justify-content: space-between; }
.panel-sub { font-size: 11px; font-weight: 400; color: var(--text-3); }

.chart-box { flex: 1; min-height: 0; position: relative; }
.panel > .echart { flex: 1; }
.chart-box .echart { height: 100%; }
.chart-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  text-align: center; color: var(--text-3); font-size: 13px; line-height: 2; pointer-events: none; }

/* KPI */
.kpi { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: 1fr 1fr; gap: 10px; }
.kpi-item {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: var(--brand-50); border: 1px solid var(--border-1);
  border-radius: var(--radius-md); padding: 8px; text-align: center;
}
.kpi-val { font-size: 24px; font-weight: 750; color: var(--brand-600); line-height: 1.2; }
.kpi-item.alert .kpi-val { color: #e05b5b; }
.kpi-name { font-size: 12px; color: var(--text-3); margin-top: 5px; }

/* 右侧告警列 */
.alarm-panel { flex: 0 0 300px; }
.alarm-list { flex: 1; min-height: 0; overflow-y: auto; padding-right: 4px; }
.alarm-row { display: flex; align-items: center; gap: 8px; padding: 9px 4px;
  border-bottom: 1px solid var(--blue-gray-300); font-size: 12px; }
.alarm-row .msg { flex: 1; min-width: 0; color: var(--text-2);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alarm-row .time { flex: none; color: var(--text-3); font-size: 11px; }
</style>
