from rest_framework import serializers
from .models import Camera, ShelfROI, CrossingLine, DwellRecord, Alarm, Setting, TrafficStat


class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = '__all__'


class ShelfROISerializer(serializers.ModelSerializer):
    class Meta:
        model = ShelfROI
        fields = '__all__'


class CrossingLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossingLine
        fields = '__all__'


class DwellRecordSerializer(serializers.ModelSerializer):
    shelf_name = serializers.CharField(source='roi.shelf_name', read_only=True)

    class Meta:
        model = DwellRecord
        fields = '__all__'


class AlarmSerializer(serializers.ModelSerializer):
    shelf_name = serializers.CharField(source='roi.shelf_name', read_only=True, default=None)
    alarm_type_display = serializers.CharField(source='get_alarm_type_display', read_only=True)

    class Meta:
        model = Alarm
        fields = '__all__'


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = '__all__'


class TrafficStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficStat
        fields = '__all__'
