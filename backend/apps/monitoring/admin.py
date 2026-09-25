from django.contrib import admin
from .models import Camera, ShelfROI, CrossingLine, TrackPoint, DwellRecord, TrafficStat, Alarm, Setting

admin.site.register([Camera, ShelfROI, CrossingLine, TrackPoint, DwellRecord, TrafficStat, Alarm, Setting])
