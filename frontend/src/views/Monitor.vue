<template>
  <div class="monitor">
    <el-row :gutter="16">
      <el-col :span="17">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>实时监控画面</span>
              <div>
                <el-tag :type="statusType" size="small" style="margin-right:8px">{{ statusText }}</el-tag>
                <el-button v-if="engineStatus !== 'running'" type="success" size="small" @click="onStart">启动分析</el-button>
                <el-button v-else type="danger" size="small" @click="onStop">停止分析</el-button>
              </div>
            </div>
          </template>
          <div class="canvas-wrap" v-loading="engineStatus === 'starting'" element-loading-text="模型加载中，首次启动需下载权重...">
            <canvas ref="canvasRef" class="monitor-canvas"></canvas>
            <div v-if="engineStatus === 'error'" class="error-tip">
              <el-icon :size="32"><WarningFilled /></el-icon>
              <p>{{ engineMessage || '推理引擎异常' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="7">
        <el-card shadow="never" class="stat-card">
          <div class="stats">
            <div class="stat-item">
              <div class="num">{{ stats.current }}</div>
              <div class="label">当前在店</div>
            </div>
            <div class="stat-item">
              <div class="num in">{{ stats.today_enter }}</div>
              <div class="label">今日进店</div>
            </div>
            <div class="stat-item">
              <div class="num out">{{ stats.today_exit }}</div>
              <div class="label">今日离店</div>
            </div>
          </div>
        </el-card>
        <el-card shadow="never" style="margin-top:16px">
          <template #header><span>货架驻留状态</span></template>
          <el-table :data="roiRows" size="small" max-height="240">
            <el-table-column prop="name" label="货架" />
            <el-table-column label="在区域人数" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.count > 0 ? 'success' : 'info'" size="small">{{ row.count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="当前驻留" width="90" align="center">
              <template #default="{ row }">{{ row.dwell > 0 ? row.dwell + 's' : '-' }}</template>
            </el-table-column>
          </el-table>
        </el-card>
        <el-card shadow="never" style="margin-top:16px">
          <template #header>
            <div class="card-header">
              <span>实时告警</span>
              <el-button link type="primary" size="small" @click="$router.push('/alarms')">全部</el-button>
            </div>
          </template>
          <div class="alarm-feed">
            <el-empty v-if="!alarms.length" description="暂无告警" :image-size="60" />
            <div v-for="a in alarms" :key="a.id" class="alarm-item" :class="a.level">
              <el-tag :type="a.level === 'critical' ? 'danger' : 'warning'" size="small">{{ typeName(a.type) }}</el-tag>
              <span class="msg">{{ a.message }}</span>
              <span class="time">{{ a.time }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCameras, getRois, getLines, startEngine, stopEngine } from '../api'
import { ReconnectWebSocket } from '../utils/ws'

interface Roi { id: number; shelf_name: string; shape_type: string; points: number[][]; color: string }
interface Line { id: number; name: string; points: number[][] }

const canvasRef = ref<HTMLCanvasElement>()
const cameraId = ref<number>(0)
const rois = ref<Roi[]>([])
const lines = ref<Line[]>([])
const engineStatus = ref('stopped')
const engineMessage = ref('')
const stats = reactive({ current: 0, today_enter: 0, today_exit: 0 })
const roiCounts = reactive<Record<string, number>>({})
const activeDwells = reactive<Record<string, number>>({})
const alarms = ref<any[]>([])
let ws: ReconnectWebSocket | null = null
let lastFrame: any = null
const img = new Image()

const statusType = computed(() => engineStatus.value === 'running' ? 'success' : engineStatus.value === 'error' ? 'danger' : 'info')
const statusText = computed(() => ({ running: '分析中', starting: '启动中', error: '异常', stopped: '已停止' }[engineStatus.value] || engineStatus.value))
const roiRows = computed(() => rois.value.map(r => ({
  id: r.id, name: r.shelf_name,
  count: roiCounts[String(r.id)] || 0,
  dwell: activeDwells[String(r.id)] || 0,
})))

function typeName(t: string) {
  return { crowd: '区域拥挤', loiter: '异常逗留', fall: '摔倒' }[t] || t
}

const SKELETON = [[0,1],[0,2],[1,3],[2,4],[5,6],[5,7],[7,9],[6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]]

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !lastFrame) return
  const ctx = canvas.getContext('2d')!
  const w = canvas.width, h = canvas.height
  ctx.clearRect(0, 0, w, h)
  if (img.complete && img.naturalWidth) ctx.drawImage(img, 0, 0, w, h)

  // ROI 区域
  for (const roi of rois.value) {
    ctx.beginPath()
    roi.points.forEach(([x, y], i) => i ? ctx.lineTo(x * w, y * h) : ctx.moveTo(x * w, y * h))
    ctx.closePath()
    ctx.fillStyle = roi.color + '33'
    ctx.fill()
    ctx.strokeStyle = roi.color
    ctx.lineWidth = 2
    ctx.stroke()
    const cx = roi.points.reduce((s, p) => s + p[0], 0) / roi.points.length * w
    const cy = roi.points.reduce((s, p) => s + p[1], 0) / roi.points.length * h
    ctx.fillStyle = roi.color
    ctx.font = 'bold 13px sans-serif'
    const count = roiCounts[String(roi.id)] || 0
    ctx.fillText(`${roi.shelf_name} (${count}人)`, cx - 40, cy)
  }

  // 入口绊线
  for (const line of lines.value) {
    const [p1, p2] = line.points
    ctx.beginPath()
    ctx.moveTo(p1[0] * w, p1[1] * h)
    ctx.lineTo(p2[0] * w, p2[1] * h)
    ctx.strokeStyle = '#F56C6C'
    ctx.lineWidth = 3
    ctx.setLineDash([8, 6])
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#F56C6C'
    ctx.fillText(line.name, p1[0] * w + 6, p1[1] * h - 6)
  }

  // 行人：轨迹、检测框、骨架
  for (const p of lastFrame.persons || []) {
    if (p.trail?.length > 1) {
      ctx.beginPath()
      p.trail.forEach(([x, y]: number[], i: number) => i ? ctx.lineTo(x * w, y * h) : ctx.moveTo(x * w, y * h))
      ctx.strokeStyle = 'rgba(103, 194, 58, .7)'
      ctx.lineWidth = 2
      ctx.stroke()
    }
    const [x1, y1, x2, y2] = p.box
    const inRoi = p.rois?.length > 0
    ctx.strokeStyle = inRoi ? '#E6A23C' : '#67C23A'
    ctx.lineWidth = 2
    ctx.strokeRect(x1 * w, y1 * h, (x2 - x1) * w, (y2 - y1) * h)
    ctx.fillStyle = inRoi ? '#E6A23C' : '#67C23A'
    ctx.fillRect(x1 * w, y1 * h - 18, 52, 16)
    ctx.fillStyle = '#fff'
    ctx.font = '11px sans-serif'
    ctx.fillText(`#${p.id}`, x1 * w + 4, y1 * h - 6)

    if (p.keypoints) {
      ctx.fillStyle = '#00d4ff'
      for (const [kx, ky] of p.keypoints) {
        if (kx > 0 && ky > 0) { ctx.beginPath(); ctx.arc(kx * w, ky * h, 2, 0, 6.3); ctx.fill() }
      }
      ctx.strokeStyle = 'rgba(0, 212, 255, .5)'
      ctx.lineWidth = 1
      for (const [a, b] of SKELETON) {
        const [ax, ay] = p.keypoints[a], [bx, by] = p.keypoints[b]
        if (ax && ay && bx && by) {
          ctx.beginPath(); ctx.moveTo(ax * w, ay * h); ctx.lineTo(bx * w, by * h); ctx.stroke()
        }
      }
    }
  }
}

function onWsMessage(data: any) {
  if (data.type === 'status') {
    engineStatus.value = data.status
    engineMessage.value = data.message
    if (data.status === 'error') ElMessage.error(data.message)
    return
  }
  if (data.type !== 'frame') return
  lastFrame = data
  stats.current = data.stats.current
  stats.today_enter = data.stats.today_enter
  stats.today_exit = data.stats.today_exit
  Object.assign(roiCounts, data.roi_counts)
  Object.keys(activeDwells).forEach(k => delete activeDwells[k])
  Object.assign(activeDwells, data.active_dwells)
  for (const a of data.alarms || []) {
    alarms.value.unshift(a)
    ElMessage({ type: a.level === 'critical' ? 'error' : 'warning', message: a.message, duration: 5000 })
  }
  if (alarms.value.length > 20) alarms.value.length = 20
  img.onload = () => draw()
  img.src = 'data:image/jpeg;base64,' + data.frame
}

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const wrap = canvas.parentElement!
  const ratio = 16 / 9
  canvas.width = wrap.clientWidth
  canvas.height = Math.round(wrap.clientWidth / ratio)
  draw()
}

async function onStart() {
  engineStatus.value = 'starting'
  try {
    const res: any = await startEngine(cameraId.value)
    if (res?.status && res.status !== 'starting') engineStatus.value = res.status
  } catch {
    engineStatus.value = 'stopped'
  }
}

async function onStop() {
  await stopEngine(cameraId.value)
  engineStatus.value = 'stopped'
}

onMounted(async () => {
  const cams: any = await getCameras()
  const list = cams.results || cams
  if (!list.length) {
    ElMessage.error('未配置摄像头，请联系管理员')
    return
  }
  cameraId.value = list[0].id
  const [r, l]: any[] = await Promise.all([getRois(), getLines()])
  rois.value = (r.results || r).filter((x: Roi) => true)
  lines.value = (l.results || l).filter((x: Line) => true)
  ws = new ReconnectWebSocket(`/ws/stream/${cameraId.value}/`)
  ws.onMessage = onWsMessage
  ws.connect()
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
  // 进入页面自动启动分析
  onStart()
})

onUnmounted(() => {
  ws?.close()
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<style scoped>
.card-header { display: flex; align-items: center; justify-content: space-between; }
.canvas-wrap { position: relative; width: 100%; min-height: 300px; background: #000; border-radius: 4px; overflow: hidden; }
.monitor-canvas { width: 100%; display: block; }
.error-tip { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #F56C6C; background: rgba(0,0,0,.6); gap: 8px; }
.stats { display: flex; justify-content: space-around; text-align: center; }
.num { font-size: 28px; font-weight: 700; color: #409EFF; }
.num.in { color: #67C23A; }
.num.out { color: #E6A23C; }
.label { font-size: 12px; color: #909399; margin-top: 4px; }
.alarm-feed { max-height: 200px; overflow-y: auto; }
.alarm-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 12px; }
.alarm-item .msg { flex: 1; color: #606266; }
.alarm-item .time { color: #c0c4cc; }
</style>
