# 寻觅客 · 新零售追踪

面向线下零售门店的视觉智能管理平台：基于 YOLOv8-Pose 实现客流统计、顾客轨迹追踪、区域热力分析、异常行为告警，输出门店运营数据，辅助零售商经营决策。

## 技术栈

| 端 | 技术 |
|---|---|
| 前端 | Vue3 + TypeScript + Vite + Element Plus + Pinia + ECharts + Axios |
| 后端 | Django 5 + Django REST Framework + Django Channels (WebSocket) |
| 数据库 | PostgreSQL（可切换 SQLite） |
| AI | YOLOv8-Pose（ultralytics）+ ByteTrack 多目标跟踪 + OpenCV |

## 功能模块

- **实时监控**：视频画面叠加检测框、骨架关键点、运动轨迹、ROI 区域、入口绊线；实时在店人数 / 进出客流 / 货架驻留状态 / 告警弹窗
- **数据大屏**：深色全屏可视化大屏，含核心指标、客流趋势、区域热力图、货架停留时长排行、最新告警，支持日期筛选与 30s 自动刷新
- **ROI 区域管理**：在监控快照上绘制矩形 / 多边形货架区域（绑定货架名称、编号、颜色），绘制入口绊线并设置进店方向
- **历史记录**：驻留记录分页查询、顾客轨迹回放
- **告警中心**：区域拥挤 / 异常逗留 / 摔倒姿态三类告警，支持筛选与处理
- **货架报表**：按货架下钻驻留人次、平均 / 总 / 最长停留、小时分布
- **系统设置**：拥挤人数阈值、逗留时长阈值、摔倒判定秒数、离开 ROI 宽限秒数

## 业务规则

- **客流统计**：入口绊线穿越计数（区分进 / 出方向，按 track_id 去重）
- **驻留判定**：行人底部中心点进入 ROI 开始计时，连续离开满 3 秒（可配）判定本次驻留结束
- **告警**：拥挤（ROI 内人数 ≥ 阈值）、逗留（单次驻留 > 阈值）、摔倒（Pose 关键点 + 宽高比启发式，持续帧确认）
- **实时链路**：推理线程读视频 → YOLO 推理 → ROI / 绊线 / 告警判定 → WebSocket 广播（约 10fps JPEG + 坐标 JSON），前端断线自动重连

## 目录结构

```
retail_analysis/
├── backend/
│   ├── retail_analysis/       # Django 配置（settings / asgi / urls）
│   ├── apps/monitoring/       # 核心应用（模型 / 视图 / 推理引擎 / WS）
│   ├── scripts/               # init_db.py 建库、init_data.py 初始化
│   ├── media/videos/          # 测试视频（test.mp4）
│   ├── weights/               # YOLO 权重（首次运行自动下载）
│   └── requirements.txt
├── frontend/
│   ├── src/views/             # 登录 / 监控 / 大屏 / ROI / 历史 / 告警 / 报表 / 设置
│   ├── src/api/               # Axios 封装与接口定义
│   ├── src/store/             # Pinia
│   └── src/utils/ws.ts        # WebSocket 自动重连
└── README.md
```

## 快速开始

### 1. 后端

```bash
# 创建虚拟环境并安装依赖（torch 体积较大，请耐心等待）
python -m venv backend/venv
backend/venv/Scripts/python -m pip install -r backend/requirements.txt   # Windows
# source backend/venv/bin/activate && pip install -r backend/requirements.txt  # Linux/Mac

# 初始化 PostgreSQL 数据库（默认 postgres/admin123@127.0.0.1:5432，可用 PGPASSWORD 等环境变量覆盖）
backend/venv/Scripts/python backend/scripts/init_db.py

# 迁移 + 初始化账号与示例数据
cd backend
venv/Scripts/python manage.py migrate
venv/Scripts/python scripts/init_data.py

# 启动（ASGI，含 WebSocket）
venv/Scripts/python manage.py runserver 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### 3. 使用

1. 访问 `http://localhost:5173`，用 **admin / admin123** 登录
2. 进入「实时监控」，自动启动分析（首次自动下载 yolov8n-pose.pt，约 6MB）
3. 进入「ROI 区域管理」，刷新底图后绘制货架区域与入口绊线
4. 「数据大屏」查看客流趋势、热力图、货架排行

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PGDATABASE` / `PGUSER` / `PGPASSWORD` / `PGHOST` / `PGPORT` | retail_analysis / postgres / admin123 / 127.0.0.1 / 5432 | 数据库连接 |
| `YOLO_WEIGHTS` | backend/weights/yolov8n-pose.pt | 模型权重路径 |
| `INFERENCE_FPS` | 10 | 推理帧率 |
| `STREAM_WIDTH` | 960 | 推流画面宽度 |

## 主要 API

| 接口 | 说明 |
|---|---|
| `POST /api/auth/login/` | 登录获取 Token |
| `GET/POST /api/rois/` | 货架 ROI 增删改查 |
| `GET/POST /api/lines/` | 入口绊线 |
| `POST /api/cameras/{id}/start/` `/stop/` | 推理引擎启停 |
| `GET /api/cameras/{id}/snapshot/` | 当前画面快照 |
| `GET /api/stats/dashboard/` | 大屏汇总数据 |
| `GET /api/stats/traffic-trend/` | 24h 客流趋势 |
| `GET /api/stats/heatmap/` | 区域热力图 |
| `GET /api/stats/dwell-by-roi/` | 各货架停留统计 |
| `GET /api/stats/roi-detail/{id}/` | 货架明细下钻 |
| `GET /api/stats/trajectory/?track_id=` | 顾客轨迹回放 |
| `GET /api/alarms/` `POST /api/alarms/{id}/handle/` | 告警查询与处理 |
| `GET/PUT /api/settings/` | 系统参数 |
| `ws://.../ws/stream/{camera_id}/` | 实时画面与数据推送 |

## 说明

- 测试视频放置于 `backend/media/videos/test.mp4`，可在 Django Admin（`/admin/`）中修改摄像头记录更换视频源；视频循环播放
- 当前为单路摄像头设计，`Camera` 表支持扩展多路（每路独立引擎线程与 WS 频道）
- Channels 使用内存 Channel Layer（单进程演示）；生产部署建议切换 Redis
