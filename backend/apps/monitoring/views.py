import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Max, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .inference import EngineManager
from .models import (Camera, ShelfROI, CrossingLine, TrackPoint, DwellRecord,
                     TrafficStat, Alarm, Setting)
from .serializers import (CameraSerializer, ShelfROISerializer, CrossingLineSerializer,
                          DwellRecordSerializer, AlarmSerializer, SettingSerializer)


# ---------- 认证 ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    user = authenticate(username=username, password=password)
    if not user:
        return Response({'detail': '用户名或密码错误'}, status=status.HTTP_400_BAD_REQUEST)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username})


@api_view(['GET'])
def profile(request):
    return Response({'username': request.user.username})


# ---------- 基础 CRUD ----------
class CameraViewSet(viewsets.ModelViewSet):
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer

    @action(detail=True, methods=['get'])
    def snapshot(self, request, pk=None):
        """最新画面快照（供 ROI 编辑器作底图）"""
        eng = EngineManager.get(int(pk))
        if eng and eng.latest_snapshot:
            return HttpResponse(eng.latest_snapshot, content_type='image/jpeg')
        return Response({'detail': '推理未启动或暂无画面'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        EngineManager.start(int(pk))
        return Response(EngineManager.status(int(pk)))

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        EngineManager.stop(int(pk))
        return Response({'status': 'stopped'})

    @action(detail=True, methods=['get'])
    def engine_status(self, request, pk=None):
        return Response(EngineManager.status(int(pk)))


class ShelfROIViewSet(viewsets.ModelViewSet):
    queryset = ShelfROI.objects.all().order_by('id')
    serializer_class = ShelfROISerializer


class CrossingLineViewSet(viewsets.ModelViewSet):
    queryset = CrossingLine.objects.all().order_by('id')
    serializer_class = CrossingLineSerializer


# ---------- 告警 ----------
class AlarmViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlarmSerializer
    queryset = Alarm.objects.all()

    def get_queryset(self):
        qs = Alarm.objects.all().order_by('-created_at')
        p = self.request.query_params
        if p.get('date'):
            qs = qs.filter(created_at__date=p['date'])
        if p.get('type'):
            qs = qs.filter(alarm_type=p['type'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        return qs

    @action(detail=True, methods=['post'])
    def handle(self, request, pk=None):
        alarm = self.get_object()
        alarm.status = 'handled'
        alarm.save(update_fields=['status'])
        return Response(AlarmSerializer(alarm).data)


# ---------- 驻留记录 ----------
class DwellRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DwellRecordSerializer
    queryset = DwellRecord.objects.all()

    def get_queryset(self):
        qs = DwellRecord.objects.select_related('roi').order_by('-enter_time')
        p = self.request.query_params
        if p.get('date'):
            qs = qs.filter(enter_time__date=p['date'])
        if p.get('roi'):
            qs = qs.filter(roi_id=p['roi'])
        if p.get('track_id'):
            qs = qs.filter(track_id=p['track_id'])
        return qs


# ---------- 系统设置 ----------
@api_view(['GET', 'PUT'])
def settings_view(request):
    if request.method == 'GET':
        result = {}
        for key, (default, label) in Setting.DEFAULTS.items():
            result[key] = {'value': Setting.get(key), 'label': label}
        return Response(result)
    for key in Setting.DEFAULTS:
        if key in request.data:
            Setting.objects.update_or_create(
                key=key,
                defaults={'value': str(request.data[key]), 'label': Setting.DEFAULTS[key][1]})
    return Response({'detail': 'ok'})


# ---------- 统计接口 ----------
def _parse_date(request):
    d = request.query_params.get('date')
    if d:
        try:
            return datetime.date.fromisoformat(d)
        except ValueError:
            pass
    return timezone.localdate()


def _camera_id(request):
    cid = request.query_params.get('camera')
    if cid:
        return int(cid)
    cam = Camera.objects.filter(is_active=True).first()
    return cam.id if cam else None


@api_view(['GET'])
def traffic_trend(request):
    """客流趋势：某日期 24 小时进/出人次"""
    d, cid = _parse_date(request), _camera_id(request)
    rows = TrafficStat.objects.filter(camera_id=cid, date=d)
    enter = [0] * 24
    exit_ = [0] * 24
    for r in rows:
        enter[r.hour] = r.enter_count
        exit_[r.hour] = r.exit_count
    return Response({'date': str(d), 'enter': enter, 'exit': exit_})


@api_view(['GET'])
def heatmap(request):
    """区域热力图：轨迹点聚合到网格（echarts heatmap 格式）"""
    d, cid = _parse_date(request), _camera_id(request)
    grid_w, grid_h = 48, 27
    qs = TrackPoint.objects.filter(camera_id=cid, ts__date=d)
    grid = {}
    for p in qs.values_list('x', 'y'):
        gx, gy = int(p[0] * grid_w), int(p[1] * grid_h)
        gx, gy = min(gx, grid_w - 1), min(gy, grid_h - 1)
        grid[(gx, gy)] = grid.get((gx, gy), 0) + 1
    data = [[gx, gy, v] for (gx, gy), v in grid.items()]
    return Response({'grid_w': grid_w, 'grid_h': grid_h, 'data': data})


@api_view(['GET'])
def dwell_by_roi(request):
    """各货架停留统计"""
    d, cid = _parse_date(request), _camera_id(request)
    rows = (DwellRecord.objects.filter(camera_id=cid, enter_time__date=d)
            .values('roi_id', 'roi__shelf_name')
            .annotate(count=Count('id'), avg_duration=Avg('duration'),
                      total_duration=Sum('duration'), max_duration=Max('duration'))
            .order_by('-total_duration'))
    return Response(list(rows))


@api_view(['GET'])
def roi_detail(request, roi_id):
    """货架明细下钻：指标 + 小时分布"""
    d, cid = _parse_date(request), _camera_id(request)
    qs = DwellRecord.objects.filter(camera_id=cid, roi_id=roi_id, enter_time__date=d)
    agg = qs.aggregate(count=Count('id'), avg_duration=Avg('duration'),
                       total=Sum('duration'), max_duration=Max('duration'))
    hourly = [0] * 24
    for r in qs.values_list('enter_time', flat=True):
        hourly[timezone.localtime(r).hour] += 1
    try:
        roi = ShelfROI.objects.get(id=roi_id)
        name = roi.shelf_name
    except ShelfROI.DoesNotExist:
        name = ''
    return Response({
        'roi_id': int(roi_id), 'shelf_name': name, 'date': str(d),
        'count': agg['count'] or 0,
        'avg_duration': round(agg['avg_duration'] or 0, 1),
        'total_duration': round(agg['total'] or 0, 1),
        'max_duration': round(agg['max_duration'] or 0, 1),
        'hourly': hourly,
    })


@api_view(['GET'])
def trajectory(request):
    """顾客轨迹回放：某 track_id 当日的轨迹点"""
    d, cid = _parse_date(request), _camera_id(request)
    track_id = request.query_params.get('track_id')
    points = list(TrackPoint.objects.filter(camera_id=cid, track_id=track_id, ts__date=d)
                  .order_by('ts').values_list('x', 'y', 'ts'))
    return Response({'track_id': track_id,
                     'points': [[round(x, 4), round(y, 4), t.strftime('%H:%M:%S')] for x, y, t in points]})


@api_view(['GET'])
def tracks(request):
    """当日出现过的 track 列表（轨迹回放选择器）"""
    d, cid = _parse_date(request), _camera_id(request)
    rows = (TrackPoint.objects.filter(camera_id=cid, ts__date=d)
            .values('track_id').annotate(points=Count('id'),
                                         first=Max('ts')).order_by('-first')[:200])
    dwells = (DwellRecord.objects.filter(camera_id=cid, enter_time__date=d)
              .values('track_id').annotate(dwell_count=Count('id'), total=Sum('duration')))
    dwell_map = {r['track_id']: r for r in dwells}
    result = []
    for r in rows:
        dw = dwell_map.get(r['track_id'], {})
        result.append({
            'track_id': r['track_id'], 'points': r['points'],
            'last_time': timezone.localtime(r['first']).strftime('%H:%M:%S') if r['first'] else '',
            'dwell_count': dw.get('dwell_count', 0),
            'total_dwell': round(dw.get('total') or 0, 1),
        })
    return Response(result)


@api_view(['GET'])
def dashboard(request):
    """大屏汇总：核心指标 + 趋势 + 货架排行 + 最新告警"""
    d, cid = _parse_date(request), _camera_id(request)
    traffic = TrafficStat.objects.filter(camera_id=cid, date=d)\
        .aggregate(enter=Sum('enter_count'), exit=Sum('exit_count'))
    dwell = DwellRecord.objects.filter(camera_id=cid, enter_time__date=d)\
        .aggregate(count=Count('id'), avg=Avg('duration'))
    top_rois = (DwellRecord.objects.filter(camera_id=cid, enter_time__date=d)
                .values('roi_id', 'roi__shelf_name')
                .annotate(count=Count('id'), avg_duration=Avg('duration'),
                          total_duration=Sum('duration'))
                .order_by('-total_duration')[:8])
    alarms_today = Alarm.objects.filter(camera_id=cid, created_at__date=d).count()
    pending_alarms = Alarm.objects.filter(camera_id=cid, status='pending').count()
    latest_alarms = AlarmSerializer(
        Alarm.objects.filter(camera_id=cid).order_by('-created_at')[:10], many=True).data
    eng = EngineManager.status(cid) if cid else {'status': 'stopped', 'message': ''}
    return Response({
        'date': str(d),
        'today_enter': traffic['enter'] or 0,
        'today_exit': traffic['exit'] or 0,
        'dwell_count': dwell['count'] or 0,
        'avg_dwell': round(dwell['avg'] or 0, 1),
        'alarms_today': alarms_today,
        'pending_alarms': pending_alarms,
        'top_rois': list(top_rois),
        'latest_alarms': latest_alarms,
        'engine': eng,
    })
