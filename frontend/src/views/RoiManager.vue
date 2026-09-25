<template>
  <el-row :gutter="16">
    <el-col :span="17">
      <el-card shadow="never">
        <template #header>
          <div class="header">
            <el-radio-group v-model="mode" size="small">
              <el-radio-button value="rect">矩形区域</el-radio-button>
              <el-radio-button value="polygon">多边形区域</el-radio-button>
              <el-radio-button value="line">入口绊线</el-radio-button>
              <el-radio-button :value="null">查看</el-radio-button>
            </el-radio-group>
            <div>
              <el-button size="small" @click="loadSnapshot">刷新底图</el-button>
              <el-button size="small" :disabled="!draftPoints.length" @click="undoStep">撤销一步</el-button>
              <el-button size="small" type="danger" plain :disabled="!draftPoints.length && !pendingShape" @click="cancelDraft">清除草稿</el-button>
            </div>
          </div>
        </template>
        <div class="editor-wrap" v-loading="snapshotLoading">
          <template v-if="snapshotOk">
            <img ref="imgRef" :src="imgSrc" class="bg" @load="onImgLoad" crossorigin="anonymous" />
            <canvas ref="canvasRef" class="overlay"
              @mousedown="onDown" @mousemove="onMove" @mouseup="onUp" @dblclick="onDblClick" />
          </template>
          <el-empty v-else description="暂无画面快照，请先在「实时监控」页启动分析">
            <el-button type="primary" @click="$router.push('/monitor')">去启动</el-button>
          </el-empty>
        </div>
        <div class="hint" v-if="mode === 'polygon'">单击添加顶点，双击结束绘制</div>
        <div class="hint" v-else-if="mode === 'rect'">按住鼠标拖拽绘制矩形</div>
        <div class="hint" v-else-if="mode === 'line'">单击两点绘制入口线，箭头方向为进店方向</div>
      </el-card>

      <el-card shadow="never" style="margin-top:16px" v-if="pendingShape">
        <template #header><span>保存区域</span></template>
        <el-form inline>
          <template v-if="pendingShape === 'line'">
            <el-form-item label="名称">
              <el-input v-model="form.name" placeholder="入口线" style="width:140px" />
            </el-form-item>
            <el-form-item>
              <el-checkbox v-model="form.flip">反转进店方向</el-checkbox>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveLine">保存绊线</el-button>
            </el-form-item>
          </template>
          <template v-else>
            <el-form-item label="货架名称">
              <el-input v-model="form.shelfName" placeholder="如：饮料货架A" style="width:140px" />
            </el-form-item>
            <el-form-item label="货架编号">
              <el-input v-model="form.shelfCode" placeholder="如：A-01" style="width:110px" />
            </el-form-item>
            <el-form-item label="颜色">
              <el-color-picker v-model="form.color" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveRoi" :disabled="!form.shelfName">保存区域</el-button>
            </el-form-item>
          </template>
        </el-form>
      </el-card>
    </el-col>

    <el-col :span="7">
      <el-card shadow="never">
        <template #header><span>已配置货架 ROI（{{ rois.length }}）</span></template>
        <el-table :data="rois" size="small" max-height="300">
          <el-table-column label="颜色" width="56">
            <template #default="{ row }"><span class="dot" :style="{ background: row.color }"></span></template>
          </el-table-column>
          <el-table-column prop="shelf_name" label="货架" />
          <el-table-column prop="shelf_code" label="编号" width="70" />
          <el-table-column label="形状" width="64">
            <template #default="{ row }">{{ row.shape_type === 'rect' ? '矩形' : '多边形' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="64">
            <template #default="{ row }">
              <el-popconfirm title="确认删除该区域？" @confirm="onDeleteRoi(row.id)">
                <template #reference><el-button link type="danger" size="small">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-card shadow="never" style="margin-top:16px">
        <template #header><span>入口绊线（{{ lines.length }}）</span></template>
        <el-table :data="lines" size="small">
          <el-table-column prop="name" label="名称" />
          <el-table-column label="操作" width="64">
            <template #default="{ row }">
              <el-popconfirm title="确认删除该绊线？" @confirm="onDeleteLine(row.id)">
                <template #reference><el-button link type="danger" size="small">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { getCameras, getRois, createRoi, deleteRoi, getLines, createLine, deleteLine } from '../api'

const mode = ref<string | null>(null)
const rois = ref<any[]>([])
const lines = ref<any[]>([])
const cameraId = ref(0)
const imgRef = ref<HTMLImageElement>()
const canvasRef = ref<HTMLCanvasElement>()
const imgSrc = ref('')
const snapshotOk = ref(false)
const snapshotLoading = ref(false)

const draftPoints = reactive<number[][]>([])   // 归一化坐标草稿
const pendingShape = ref<string | null>(null)
const form = reactive({ shelfName: '', shelfCode: '', color: '#409EFF', name: '入口线', flip: false })
let drawingRect = false
let rectStart: number[] | null = null

async function loadData() {
  const cams: any = await getCameras()
  const list = cams.results || cams
  if (!list.length) return
  cameraId.value = list[0].id
  const [r, l]: any[] = await Promise.all([getRois(), getLines()])
  rois.value = r.results || r
  lines.value = l.results || l
  loadSnapshot()
}

async function loadSnapshot() {
  snapshotLoading.value = true
  snapshotOk.value = false
  try {
    // 用 axios 携带 Token 拉取快照（<img> 无法带 Authorization 头）
    const blob: any = await request.get(`/cameras/${cameraId.value}/snapshot/`, { responseType: 'blob' })
    imgSrc.value = URL.createObjectURL(blob)
    snapshotOk.value = true   // <img> 加载成功后 onImgLoad 会初始化画布
  } catch {
    snapshotOk.value = false
  } finally {
    snapshotLoading.value = false
  }
}

function onImgLoad() {
  snapshotOk.value = true
  snapshotLoading.value = false
  const canvas = canvasRef.value!, img = imgRef.value!
  canvas.width = img.clientWidth
  canvas.height = img.clientHeight
  redraw()
}

function norm(e: MouseEvent): number[] {
  const canvas = canvasRef.value!
  const rect = canvas.getBoundingClientRect()
  return [(e.clientX - rect.left) / canvas.width, (e.clientY - rect.top) / canvas.height]
}

function onDown(e: MouseEvent) {
  const p = norm(e)
  if (mode.value === 'rect') {
    drawingRect = true
    rectStart = p
    draftPoints.length = 0
    draftPoints.push(p)
  } else if (mode.value === 'polygon') {
    draftPoints.push(p)
    redraw()
  } else if (mode.value === 'line') {
    draftPoints.push(p)
    if (draftPoints.length === 2) pendingShape.value = 'line'
    redraw()
  }
}

function onMove(e: MouseEvent) {
  if (mode.value === 'rect' && drawingRect && rectStart) {
    draftPoints.splice(1, 1, norm(e))
    redraw()
  }
}

function onUp() {
  if (mode.value === 'rect' && drawingRect) {
    drawingRect = false
    if (draftPoints.length === 2) {
      const [a, b] = draftPoints
      if (Math.abs(a[0] - b[0]) > 0.01 && Math.abs(a[1] - b[1]) > 0.01) pendingShape.value = 'rect'
    }
    redraw()
  }
}

function onDblClick() {
  if (mode.value === 'polygon' && draftPoints.length >= 3) {
    pendingShape.value = 'polygon'
    redraw()
  }
}

/** 撤销一步：多边形/绊线移除上一个点，矩形取消本次拖拽 */
function undoStep() {
  if (!draftPoints.length) return
  if (mode.value === 'rect') {
    // 矩形一次拖拽即成形，撤销一步 = 清除矩形草稿
    draftPoints.length = 0
    rectStart = null
    pendingShape.value = null
  } else {
    draftPoints.pop()
    // 顶点数不足时退出待保存状态
    if (mode.value === 'polygon' && draftPoints.length < 3) pendingShape.value = null
    if (mode.value === 'line' && draftPoints.length < 2) pendingShape.value = null
  }
  redraw()
}

function cancelDraft() {
  draftPoints.length = 0
  pendingShape.value = null
  rectStart = null
  redraw()
}

function redraw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')!
  const w = canvas.width, h = canvas.height
  ctx.clearRect(0, 0, w, h)

  // 已有 ROI
  for (const roi of rois.value) {
    ctx.beginPath()
    roi.points.forEach(([x, y]: number[], i: number) => i ? ctx.lineTo(x * w, y * h) : ctx.moveTo(x * w, y * h))
    ctx.closePath()
    ctx.fillStyle = roi.color + '33'
    ctx.fill()
    ctx.strokeStyle = roi.color
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.fillStyle = roi.color
    ctx.font = '12px sans-serif'
    ctx.fillText(roi.shelf_name, roi.points[0][0] * w + 4, roi.points[0][1] * h - 6)
  }
  // 已有绊线
  for (const line of lines.value) {
    drawLine(ctx, line.points, '#F56C6C', line.name, w, h)
  }
  // 草稿
  if (draftPoints.length) {
    ctx.strokeStyle = '#FFEB3B'
    ctx.fillStyle = '#FFEB3B'
    ctx.lineWidth = 2
    ctx.beginPath()
    draftPoints.forEach(([x, y], i) => i ? ctx.lineTo(x * w, y * h) : ctx.moveTo(x * w, y * h))
    if (mode.value === 'rect' && draftPoints.length === 2) {
      const [a, b] = draftPoints
      ctx.strokeRect(a[0] * w, a[1] * h, (b[0] - a[0]) * w, (b[1] - a[1]) * h)
    } else {
      ctx.stroke()
      for (const [x, y] of draftPoints) { ctx.beginPath(); ctx.arc(x * w, y * h, 4, 0, 6.3); ctx.fill() }
    }
    if (pendingShape.value === 'line' && draftPoints.length === 2) {
      drawArrow(ctx, draftPoints, w, h)
    }
  }
}

function drawLine(ctx: CanvasRenderingContext2D, points: number[][], color: string, label: string, w: number, h: number) {
  const [p1, p2] = points
  ctx.beginPath()
  ctx.moveTo(p1[0] * w, p1[1] * h)
  ctx.lineTo(p2[0] * w, p2[1] * h)
  ctx.strokeStyle = color
  ctx.lineWidth = 3
  ctx.setLineDash([8, 6])
  ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = color
  ctx.font = '12px sans-serif'
  ctx.fillText(label, p1[0] * w + 6, p1[1] * h - 6)
}

function drawArrow(ctx: CanvasRenderingContext2D, points: number[][], w: number, h: number) {
  const [p1, p2] = points
  const mx = (p1[0] + p2[0]) / 2 * w, my = (p1[1] + p2[1]) / 2 * h
  const dx = p2[0] - p1[0], dy = p2[1] - p1[1]
  const dir = enterVec(dx, dy)
  ctx.beginPath()
  ctx.moveTo(mx, my)
  ctx.lineTo(mx + dir[0] * 30, my + dir[1] * 30)
  ctx.strokeStyle = '#FFEB3B'
  ctx.lineWidth = 2
  ctx.stroke()
  ctx.fillStyle = '#FFEB3B'
  ctx.fillText('进店', mx + dir[0] * 34, my + dir[1] * 34)
}

function enterVec(dx: number, dy: number): number[] {
  // 垂直于绊线的单位向量（默认取法向之一），flip 时反向
  const len = Math.hypot(dx, dy) || 1
  const nx = -dy / len, ny = dx / len
  const sign = form.flip ? -1 : 1
  return [nx * sign, ny * sign]
}

async function saveRoi() {
  let points = draftPoints.map(p => p)
  let shape = pendingShape.value!
  if (shape === 'rect') {
    const [a, b] = points
    const [x1, y1] = [Math.min(a[0], b[0]), Math.min(a[1], b[1])]
    const [x2, y2] = [Math.max(a[0], b[0]), Math.max(a[1], b[1])]
    points = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
  }
  await createRoi({
    camera: cameraId.value, shelf_name: form.shelfName, shelf_code: form.shelfCode,
    shape_type: shape, points: points.map(p => p.map(v => +v.toFixed(4))), color: form.color,
  })
  ElMessage.success('区域已保存')
  cancelDraft()
  form.shelfName = ''
  form.shelfCode = ''
  const r: any = await getRois()
  rois.value = r.results || r
  redraw()
}

async function saveLine() {
  const dx = draftPoints[1][0] - draftPoints[0][0]
  const dy = draftPoints[1][1] - draftPoints[0][1]
  await createLine({
    camera: cameraId.value, name: form.name,
    points: draftPoints.map(p => p.map(v => +v.toFixed(4))),
    enter_direction: [enterVec(dx, dy).map(v => +v.toFixed(4))],
  })
  ElMessage.success('绊线已保存')
  cancelDraft()
  const l: any = await getLines()
  lines.value = l.results || l
  redraw()
}

async function onDeleteRoi(id: number) {
  await deleteRoi(id)
  rois.value = rois.value.filter(r => r.id !== id)
  redraw()
}

async function onDeleteLine(id: number) {
  await deleteLine(id)
  lines.value = lines.value.filter(l => l.id !== id)
  redraw()
}

function onKeydown(e: KeyboardEvent) {
  // Ctrl+Z 撤销上一步画笔（输入框聚焦时不拦截）
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA') return
    e.preventDefault()
    undoStep()
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.editor-wrap { position: relative; width: 100%; background: #000; border-radius: 4px; overflow: hidden; min-height: 200px; display: flex; align-items: center; justify-content: center; }
.bg { width: 100%; display: block; user-select: none; -webkit-user-drag: none; }
.overlay { position: absolute; top: 0; left: 0; cursor: crosshair; }
.hint { margin-top: 8px; font-size: 12px; color: #909399; }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
</style>
