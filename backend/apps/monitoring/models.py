from django.db import models


class Camera(models.Model):
    """摄像头/视频源，单路起步，可扩展多路"""
    name = models.CharField('名称', max_length=64)
    video_path = models.CharField('视频文件路径', max_length=255,
                                  default='media/videos/test.mp4')
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '摄像头'

    def __str__(self):
        return self.name


class ShelfROI(models.Model):
    """货架感兴趣区域（矩形/多边形）"""
    SHAPE_CHOICES = [('rect', '矩形'), ('polygon', '多边形')]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='rois')
    shelf_name = models.CharField('货架名称', max_length=64)
    shelf_code = models.CharField('货架编号', max_length=32, blank=True, default='')
    shape_type = models.CharField('形状', max_length=16, choices=SHAPE_CHOICES, default='polygon')
    # 归一化坐标（0~1），rect: [[x1,y1],[x2,y2]]；polygon: [[x,y],...]
    points = models.JSONField('坐标点')
    color = models.CharField('显示颜色', max_length=16, default='#409EFF')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '货架ROI'

    def __str__(self):
        return self.shelf_name


class CrossingLine(models.Model):
    """入口绊线，穿越计数（区分进/出方向）"""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='lines')
    name = models.CharField('名称', max_length=64, default='入口线')
    # 归一化坐标 [[x1,y1],[x2,y2]]
    points = models.JSONField('线段坐标')
    # 进店方向：线段法向中指向店内的一侧标记，用向量 [dx,dy] 表示
    enter_direction = models.JSONField('进店方向向量', default=[[0, 1]])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '入口绊线'

    def __str__(self):
        return self.name


class TrackPoint(models.Model):
    """行人轨迹采样点（约每秒一次/人），用于热力图与轨迹回放"""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    track_id = models.IntegerField('跟踪ID', db_index=True)
    x = models.FloatField('归一化X')
    y = models.FloatField('归一化Y')
    ts = models.DateTimeField('时间', db_index=True)

    class Meta:
        verbose_name = '轨迹点'
        indexes = [models.Index(fields=['camera', 'ts'])]


class DwellRecord(models.Model):
    """顾客在货架 ROI 的一次驻留记录"""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    roi = models.ForeignKey(ShelfROI, on_delete=models.CASCADE, related_name='dwell_records')
    track_id = models.IntegerField('跟踪ID')
    enter_time = models.DateTimeField('进入时间')
    leave_time = models.DateTimeField('离开时间', null=True, blank=True)
    duration = models.FloatField('停留时长(秒)', default=0)
    is_active = models.BooleanField('进行中', default=True)

    class Meta:
        verbose_name = '驻留记录'
        indexes = [models.Index(fields=['roi', 'enter_time'])]


class TrafficStat(models.Model):
    """客流统计（按摄像头+日期+小时聚合）"""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    date = models.DateField('日期', db_index=True)
    hour = models.IntegerField('小时')
    enter_count = models.IntegerField('进店人次', default=0)
    exit_count = models.IntegerField('离店人次', default=0)

    class Meta:
        verbose_name = '客流统计'
        unique_together = ('camera', 'date', 'hour')


class Alarm(models.Model):
    """异常行为告警"""
    TYPE_CHOICES = [
        ('crowd', '区域拥挤'),
        ('loiter', '异常逗留'),
        ('fall', '摔倒/异常姿态'),
    ]
    STATUS_CHOICES = [('pending', '未处理'), ('handled', '已处理')]
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    roi = models.ForeignKey(ShelfROI, on_delete=models.SET_NULL, null=True, blank=True)
    alarm_type = models.CharField('类型', max_length=16, choices=TYPE_CHOICES)
    level = models.CharField('级别', max_length=8, default='warning')
    message = models.CharField('内容', max_length=255)
    track_id = models.IntegerField('跟踪ID', null=True, blank=True)
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('时间', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = '告警'


class Setting(models.Model):
    """系统参数 key-value"""
    key = models.CharField('键', max_length=64, unique=True)
    value = models.CharField('值', max_length=255)
    label = models.CharField('说明', max_length=128, default='')

    class Meta:
        verbose_name = '系统设置'

    DEFAULTS = {
        'crowd_threshold': ('3', '区域拥挤人数阈值'),
        'loiter_seconds': ('60', '异常逗留时长阈值(秒)'),
        'fall_seconds': ('3', '摔倒姿态持续判定(秒)'),
        'dwell_grace_seconds': ('3', '离开ROI宽限(秒)'),
    }

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            if key in cls.DEFAULTS:
                return cls.DEFAULTS[key][0]
            return default

    @classmethod
    def get_int(cls, key, default=0):
        try:
            return int(cls.get(key, default))
        except (TypeError, ValueError):
            return default
