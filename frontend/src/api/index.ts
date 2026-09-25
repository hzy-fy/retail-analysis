import request from './request'

// 摄像头
export const getCameras = () => request.get('/cameras/')
export const startEngine = (id: number) => request.post(`/cameras/${id}/start/`)
export const stopEngine = (id: number) => request.post(`/cameras/${id}/stop/`)
export const getEngineStatus = (id: number) => request.get(`/cameras/${id}/engine_status/`)
export const snapshotUrl = (id: number) => `/api/cameras/${id}/snapshot/`

// ROI 与绊线
export const getRois = () => request.get('/rois/')
export const createRoi = (data: any) => request.post('/rois/', data)
export const updateRoi = (id: number, data: any) => request.put(`/rois/${id}/`, data)
export const deleteRoi = (id: number) => request.delete(`/rois/${id}/`)
export const getLines = () => request.get('/lines/')
export const createLine = (data: any) => request.post('/lines/', data)
export const deleteLine = (id: number) => request.delete(`/lines/${id}/`)

// 告警
export const getAlarms = (params?: any) => request.get('/alarms/', { params })
export const handleAlarm = (id: number) => request.post(`/alarms/${id}/handle/`)

// 驻留记录
export const getDwellRecords = (params?: any) => request.get('/dwell-records/', { params })

// 统计
export const getDashboard = (params?: any) => request.get('/stats/dashboard/', { params })
export const getTrafficTrend = (params?: any) => request.get('/stats/traffic-trend/', { params })
export const getHeatmap = (params?: any) => request.get('/stats/heatmap/', { params })
export const getDwellByRoi = (params?: any) => request.get('/stats/dwell-by-roi/', { params })
export const getRoiDetail = (roiId: number, params?: any) => request.get(`/stats/roi-detail/${roiId}/`, { params })
export const getTrajectory = (params?: any) => request.get('/stats/trajectory/', { params })
export const getTracks = (params?: any) => request.get('/stats/tracks/', { params })

// 设置
export const getSettings = () => request.get('/settings/')
export const saveSettings = (data: any) => request.put('/settings/', data)
