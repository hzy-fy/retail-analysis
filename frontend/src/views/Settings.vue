<template>
  <div>
    <el-card shadow="never">
      <template #header><span>系统设置</span></template>
      <el-form label-width="220px" style="max-width:640px">
        <el-form-item label="区域拥挤人数阈值（人）">
          <el-input-number v-model="form.crowd_threshold" :min="1" :max="20" />
          <span class="hint">某 ROI 内人数超过此值触发拥挤告警</span>
        </el-form-item>
        <el-form-item label="异常逗留时长阈值（秒）">
          <el-input-number v-model="form.loiter_seconds" :min="10" :max="600" />
          <span class="hint">单次驻留超过此值触发逗留告警</span>
        </el-form-item>
        <el-form-item label="摔倒判定持续帧数（秒）">
          <el-input-number v-model="form.fall_seconds" :min="1" :max="10" />
          <span class="hint">持续检测到的姿态异常秒数</span>
        </el-form-item>
        <el-form-item label="离开 ROI 宽限（秒）">
          <el-input-number v-model="form.dwell_grace_seconds" :min="1" :max="10" />
          <span class="hint">离开区域后宽限几秒再判定结束驻留</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSave">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, saveSettings } from '../api'

const form = ref<any>({ crowd_threshold: 3, loiter_seconds: 60, fall_seconds: 3, dwell_grace_seconds: 3 })

async function load() {
  const res: any = await getSettings()
  for (const k of Object.keys(form.value)) {
    if (res[k]) form.value[k] = Number(res[k].value) || form.value[k]
  }
}

async function onSave() {
  await saveSettings(form.value)
  ElMessage.success('设置已保存')
}

onMounted(load)
</script>

<style scoped>
.hint { margin-left: 12px; font-size: 12px; color: #909399; }
</style>
