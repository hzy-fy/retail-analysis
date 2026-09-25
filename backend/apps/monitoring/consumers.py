import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class StreamConsumer(AsyncWebsocketConsumer):
    """监控画面/实时数据推送：ws/stream/<camera_id>/"""

    async def connect(self):
        self.camera_id = self.scope['url_route']['kwargs']['camera_id']
        self.group = f'camera_{self.camera_id}'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        # 连接后立即推送当前引擎状态，避免前端停留在旧的 starting 状态
        from .inference import EngineManager
        status = await database_sync_to_async(EngineManager.status)(int(self.camera_id))
        await self.send(text_data=json.dumps({'type': 'status', **status}))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        pass  # 当前为单向推送，保留入口

    async def stream_frame(self, event):
        await self.send(text_data=json.dumps({'type': 'frame', **event['data']}))

    async def stream_status(self, event):
        await self.send(text_data=json.dumps({'type': 'status', **event['data']}))
