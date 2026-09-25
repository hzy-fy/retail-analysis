from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('cameras', views.CameraViewSet)
router.register('rois', views.ShelfROIViewSet)
router.register('lines', views.CrossingLineViewSet)
router.register('alarms', views.AlarmViewSet)
router.register('dwell-records', views.DwellRecordViewSet)

urlpatterns = [
    path('auth/login/', views.login),
    path('auth/profile/', views.profile),
    path('settings/', views.settings_view),
    path('stats/dashboard/', views.dashboard),
    path('stats/traffic-trend/', views.traffic_trend),
    path('stats/heatmap/', views.heatmap),
    path('stats/dwell-by-roi/', views.dwell_by_roi),
    path('stats/roi-detail/<int:roi_id>/', views.roi_detail),
    path('stats/trajectory/', views.trajectory),
    path('stats/tracks/', views.tracks),
    path('', include(router.urls)),
]
