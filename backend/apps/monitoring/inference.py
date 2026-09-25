"""YOLOv8-Pose 推理引擎：目标跟踪、ROI 驻留统计、绊线客流、异常告警、热力/轨迹采集"""
import base64
import threading
import time
from collections import defaultdict
from datetime import date as date_cls

import cv2
import numpy as np
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import close_old_connections
from django.db.models import F
from django.utils import timezone

from .models import (Camera, ShelfROI, CrossingLine, TrackPoint, DwellRecord,
                     TrafficStat, Alarm, Setting)


def _seg_intersect(p1, p2, p3, p4):
    """判断线段 p1p2 与 p3p4 是否相交"""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


class CameraEngine(threading.Thread):
    """单路摄像头推理线程"""

    def __init__(self, camera_id):
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.stop_event = threading.Event()
        self.status = 'starting'      # starting/running/error/stopped
        self.message = ''
        self.latest_snapshot = None   # 最新原始帧 JPEG bytes（供 ROI 编辑器取图）
        self.frame_size = (0, 0)      # 原始视频宽高
        self._today_enter = 0
        self._today_exit = 0
        self._today_date = None

    # ---------- 主循环 ----------
    def run(self):
        try:
            self._run()
        except Exception as e:  # noqa
            self.status = 'error'
            self.message = f'推理异常: {e}'
            self._broadcast_status()
        finally:
            close_old_connections()

    def _run(self):
        camera = Camera.objects.filter(id=self.camera_id).first()
        if not camera:
            self.status, self.message = 'error', '摄像头不存在'
            self._broadcast_status()
            return
        video = str(settings.BASE_DIR / camera.video_path) if not camera.video_path.startswith(('/', 'C:')) else camera.video_path
        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            self.status, self.message = 'error', f'无法打开视频: {video}'
            self._broadcast_status()
            return

        from ultralytics import YOLO
        model = YOLO(settings.YOLO_WEIGHTS)

        fps_target = settings.INFERENCE_FPS
        stream_w = settings.STREAM_WIDTH
        channel_layer = get_channel_layer()
        group = f'camera_{self.camera_id}'

        # 运行时状态
        roi_version = [0, time.time()]  # 简单缓存
        rois, lines = [], []
        dwell_state = {}          # (track_id, roi_id) -> {'record': DwellRecord, 'last_inside': ts}
        track_trail = defaultdict(list)   # track_id -> [(x,y), ...] 最近轨迹
        track_last_point = {}     # track_id -> ts 上次入库轨迹点时间
        track_prev_center = {}    # track_id -> (x, y) 上一帧中心
        line_cooldown = {}        # (track_id, line_id) -> ts 穿越冷却
        fall_state = {}           # track_id -> {'count': int, 'alarmed': bool}
        crowd_cooldown = {}       # roi_id -> ts
        loiter_alarmed = set()    # (track_id, roi_id)
        new_alarms = []

        self.status = 'running'
        self._broadcast_status()

        while not self.stop_event.is_set():
            t0 = time.time()
            ok, frame = cap.read()
            if not ok:  # 循环播放演示视频
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            h, w = frame.shape[:2]
            self.frame_size = (w, h)

            # ROI/绊线每 5 秒热更新
            if time.time() - roi_version[1] > 5:
                rois = list(ShelfROI.objects.filter(camera_id=self.camera_id))
                lines = list(CrossingLine.objects.filter(camera_id=self.camera_id))
                roi_version[1] = time.time()

            results = model.track(frame, persist=True, classes=[0], verbose=False,
                                  tracker='bytetrack.yaml', imgsz=640)[0]

            now = timezone.now()
            today = now.date()
            if self._today_date != today:  # 跨天重置内存计数
                self._today_date = today
                stat = TrafficStat.objects.filter(camera_id=self.camera_id, date=today)
                self._today_enter = sum(s.enter_count for s in stat)
                self._today_exit = sum(s.exit_count for s in stat)

            persons = []
            roi_inside = defaultdict(set)   # roi_id -> {track_id}
            active_track_ids = set()

            boxes = results.boxes
            if boxes is not None and boxes.id is not None:
                kpts = results.keypoints.xy.cpu().numpy() if results.keypoints is not None else None
                xyxy = boxes.xyxy.cpu().numpy()
                ids = boxes.id.cpu().numpy().astype(int)
                for i, tid in enumerate(ids):
                    x1, y1, x2, y2 = [float(v) for v in xyxy[i]]
                    tid = int(tid)
                    cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
                    foot_x, foot_y = cx, y2 / h   # 用底部中心做区域判定更贴近真实站位
                    active_track_ids.add(tid)

                    # ---- ROI 驻留 ----
                    inside_roi_ids = []
                    for roi in rois:
                        pts = np.array([[p[0] * w, p[1] * h] for p in roi.points], dtype=np.int32)
                        inside = cv2.pointPolygonTest(pts, (foot_x * w, foot_y * h), False) >= 0
                        if inside:
                            inside_roi_ids.append(roi.id)
                            roi_inside[roi.id].add(tid)
                        key = (tid, roi.id)
                        if inside:
                            if key not in dwell_state:
                                rec = DwellRecord.objects.create(
                                    camera_id=self.camera_id, roi=roi, track_id=tid, enter_time=now)
                                dwell_state[key] = {'record': rec, 'last_inside': time.time()}
                            else:
                                dwell_state[key]['last_inside'] = time.time()
                            # 异常逗留
                            dwell_sec = (now - dwell_state[key]['record'].enter_time).total_seconds()
                            if dwell_sec > Setting.get_int('loiter_seconds', 60) and key not in loiter_alarmed:
                                loiter_alarmed.add(key)
                                new_alarms.append(self._make_alarm(
                                    camera, 'loiter', f'顾客#{tid} 在「{roi.shelf_name}」逗留超过 {int(dwell_sec)} 秒',
                                    track_id=tid, roi=roi))

                    # ---- 绊线客流 ----
                    prev = track_prev_center.get(tid)
                    if prev:
                        for line in lines:
                            lp = [[p[0], p[1]] for p in line.points]
                            if (tid, line.id) in line_cooldown and \
                                    time.time() - line_cooldown[(tid, line.id)] < 3:
                                continue
                            if _seg_intersect(prev, (cx, cy), lp[0], lp[1]):
                                line_vec = (lp[1][0] - lp[0][0], lp[1][1] - lp[0][1])
                                move_vec = (cx - prev[0], cy - prev[1])
                                cross_z = line_vec[0] * move_vec[1] - line_vec[1] * move_vec[0]
                                enter_vec = line.enter_direction[0] if line.enter_direction else [0, 1]
                                # 进店方向与 cross_z 符号对应
                                is_enter = (cross_z > 0) == (enter_vec[0] * line_vec[1] - enter_vec[1] * line_vec[0] > 0)
                                line_cooldown[(tid, line.id)] = time.time()
                                self._count_traffic(camera, today, now.hour, is_enter)
                    track_prev_center[tid] = (cx, cy)

                    # ---- 摔倒/异常姿态（启发式）----
                    bw, bh = (x2 - x1) / w, (y2 - y1) / h
                    fallen = bh > 1e-4 and bw / bh > 1.1
                    if not fallen and kpts is not None and i < len(kpts):
                        kp = kpts[i]
                        if len(kp) >= 17:
                            shoulder_y = (kp[5][1] + kp[6][1]) / 2
                            hip_y = (kp[11][1] + kp[12][1]) / 2
                            ankle_y = (kp[15][1] + kp[16][1]) / 2
                            if abs(shoulder_y - ankle_y) < (y2 - y1) * 0.35 and abs(shoulder_y - hip_y) < (y2 - y1) * 0.2:
                                fallen = True
                    st = fall_state.setdefault(tid, {'count': 0, 'alarmed': False})
                    st['count'] = st['count'] + 1 if fallen else 0
                    if st['count'] >= Setting.get_int('fall_seconds', 3) * fps_target and not st['alarmed']:
                        st['alarmed'] = True
                        new_alarms.append(self._make_alarm(
                            camera, 'fall', f'检测到顾客#{tid} 疑似摔倒，请立即查看', track_id=tid, level='critical'))

                    # ---- 轨迹采集（每人每秒1点）----
                    if now.timestamp() - track_last_point.get(tid, 0) >= 1:
                        track_last_point[tid] = now.timestamp()
                        TrackPoint.objects.create(camera_id=self.camera_id, track_id=tid, x=round(cx, 4), y=round(cy, 4), ts=now)

                    # 前端展示用短时轨迹
                    trail = track_trail[tid]
                    trail.append([round(cx, 4), round(cy, 4)])
                    if len(trail) > 30:
                        trail.pop(0)

                    persons.append({
                        'id': int(tid),
                        'box': [round(x1 / w, 4), round(y1 / h, 4), round(x2 / w, 4), round(y2 / h, 4)],
                        'center': [round(cx, 4), round(cy, 4)],
                        'rois': inside_roi_ids,
                        'trail': trail[-15:],
                        'keypoints': (kpts[i] / [w, h]).round(4).tolist() if kpts is not None and i < len(kpts) else None,
                    })

            # ---- 驻留结束判定：离开超过宽限秒数 ----
            grace = Setting.get_int('dwell_grace_seconds', 3)
            for key in list(dwell_state.keys()):
                tid, roi_id = key
                if tid not in active_track_ids or time.time() - dwell_state[key]['last_inside'] > grace:
                    rec = dwell_state[key]['record']
                    rec.leave_time = now
                    rec.duration = max((now - rec.enter_time).total_seconds(), 0)
                    rec.is_active = False
                    rec.save(update_fields=['leave_time', 'duration', 'is_active'])
                    del dwell_state[key]
                    loiter_alarmed.discard(key)

            # ---- 区域拥挤 ----
            crowd_th = Setting.get_int('crowd_threshold', 3)
            for roi in rois:
                n = len(roi_inside.get(roi.id, ()))
                if n >= crowd_th and time.time() - crowd_cooldown.get(roi.id, 0) > 30:
                    crowd_cooldown[roi.id] = time.time()
                    new_alarms.append(self._make_alarm(
                        camera, 'crowd', f'「{roi.shelf_name}」区域当前 {n} 人，超过拥挤阈值 {crowd_th}', roi=roi))

            # 清理消失目标的状态
            for tid in list(track_prev_center.keys()):
                if tid not in active_track_ids:
                    track_prev_center.pop(tid, None)
                    fall_state.pop(tid, None)
                    track_trail.pop(tid, None)

            # ---- 推流帧 ----
            scale = stream_w / w
            out = cv2.resize(frame, (stream_w, int(h * scale))) if stream_w < w else frame
            self.latest_snapshot = cv2.imencode('.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
            jpg = base64.b64encode(
                cv2.imencode('.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 60])[1]).decode()

            payload_alarms = []
            for a in new_alarms:
                payload_alarms.append({'id': a.id, 'type': a.alarm_type, 'message': a.message,
                                       'level': a.level, 'time': a.created_at.strftime('%H:%M:%S')})
            new_alarms = []

            async_to_sync(channel_layer.group_send)(group, {
                'type': 'stream.frame',
                'data': {
                    'frame': jpg,
                    'ts': now.strftime('%H:%M:%S'),
                    'persons': persons,
                    'stats': {
                        'current': len(active_track_ids),
                        'today_enter': self._today_enter,
                        'today_exit': self._today_exit,
                    },
                    'roi_counts': {str(r.id): len(roi_inside.get(r.id, ())) for r in rois},
                    'active_dwells': {
                        str(key[1]): round(time.time() - dwell_state[key]['record'].enter_time.timestamp(), 1)
                        for key in dwell_state if key[0] in active_track_ids
                    },
                    'alarms': payload_alarms,
                },
            })

            close_old_connections()
            elapsed = time.time() - t0
            time.sleep(max(0, 1.0 / fps_target - elapsed))

        cap.release()
        self.status = 'stopped'
        self._broadcast_status()

    # ---------- 工具 ----------
    def _make_alarm(self, camera, alarm_type, message, track_id=None, roi=None, level='warning'):
        return Alarm.objects.create(camera=camera, roi=roi, alarm_type=alarm_type,
                                    message=message, track_id=track_id, level=level)

    def _count_traffic(self, camera, today, hour, is_enter):
        stat, _ = TrafficStat.objects.get_or_create(camera=camera, date=today, hour=hour)
        if is_enter:
            stat.enter_count = F('enter_count') + 1
            self._today_enter += 1
        else:
            stat.exit_count = F('exit_count') + 1
            self._today_exit += 1
        stat.save(update_fields=['enter_count'] if is_enter else ['exit_count'])

    def _broadcast_status(self):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(f'camera_{self.camera_id}', {
            'type': 'stream.status',
            'data': {'status': self.status, 'message': self.message},
        })

    def stop(self):
        self.stop_event.set()


class EngineManager:
    """推理引擎管理器（单例）"""
    _engines = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, camera_id):
        with cls._lock:
            eng = cls._engines.get(camera_id)
            if eng and eng.is_alive():
                return eng
            eng = CameraEngine(camera_id)
            cls._engines[camera_id] = eng
            eng.start()
            return eng

    @classmethod
    def stop(cls, camera_id):
        with cls._lock:
            eng = cls._engines.get(camera_id)
            if eng:
                eng.stop()
                cls._engines.pop(camera_id, None)

    @classmethod
    def get(cls, camera_id):
        return cls._engines.get(camera_id)

    @classmethod
    def status(cls, camera_id):
        eng = cls._engines.get(camera_id)
        if not eng:
            return {'status': 'stopped', 'message': '未启动'}
        return {'status': eng.status, 'message': eng.message}
