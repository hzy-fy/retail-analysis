import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retail_analysis.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User
from apps.monitoring.models import Camera, Setting

# 创建演示账号
u, _ = User.objects.get_or_create(username='admin')
u.set_password('admin123')
u.save()
print('user ok')

# 创建默认摄像头（关联已存在的测试视频）
Camera.objects.get_or_create(
    id=1,
    defaults={'name': '默认摄像头', 'video_path': 'media/videos/test.mp4', 'is_active': True}
)
print('camera ok')

# 初始化系统默认设置
for key, (default, label) in Setting.DEFAULTS.items():
    Setting.objects.get_or_create(key=key, defaults={'value': default, 'label': label})
print('settings ok')
