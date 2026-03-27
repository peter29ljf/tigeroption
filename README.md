# OptionFlow Pro

美股期权大单智能监控平台 — 专为华人投资者设计

## 功能特性

- **实时监控** — 10只热门美股期权大单（NVDA, AAPL, TSLA, SPY, QQQ, AMZN, MSFT, META, GOOGL, AMD）
- **大单筛选** — 溢价 >$10万 自动过滤
- **4维评分** — 溢价规模 / Vol-OI比 / 成交方向 / 扫单识别，0-100分
- **AI中文解读** — Claude API 生成中文分析（score≥70触发）
- **微信推送** — 高评分大单实时推送到微信
- **中文界面** — 北京时间 + 人民币换算 + 全中文UI

## 技术栈

| 层级 | 技术 |
|------|------|
| 数据采集 | Python + tigeropen SDK |
| 消息队列 | Redis Streams |
| 后端 | FastAPI + Celery |
| 数据库 | PostgreSQL + TimescaleDB |
| AI | Anthropic Claude API |
| 前端 | Next.js 15 + React 19 + Tailwind CSS 4 + Zustand |

## 快速开始

### 1. 环境准备

```bash
cp .env.example .env
# 编辑 .env 填入实际配置（Tiger API、Claude API Key 等）
```

### 2. 放置 Tiger API 密钥

```bash
mkdir -p secrets
cp /path/to/tiger_openapi_config.properties secrets/
```

### 3. 启动所有服务

```bash
docker-compose up -d
```

服务将在以下端口启动：
- 前端：http://localhost:3000
- API文档：http://localhost:8000/docs
- PostgreSQL：localhost:5432
- Redis：localhost:6379

### 4. 仅开发后端

```bash
# 启动基础设施
docker-compose up -d db redis

# 安装依赖
pip install -e .

# 分别启动各服务
python -m services.collector.main
python -m services.processor.main
uvicorn services.api.main:app --reload --port 8000
```

### 5. 仅开发前端

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
optionflow-pro/
├── docker-compose.yml          # Docker 编排
├── config/settings.py          # Pydantic 统一配置
├── services/
│   ├── collector/              # 数据采集（Tiger API 轮询 + WebSocket）
│   ├── processor/              # 评分 + 扫单检测 + AI解读 + 入库
│   └── api/                    # FastAPI REST + WebSocket + 微信推送
├── frontend/                   # Next.js 前端
├── scripts/init_db.sql         # TimescaleDB 初始化
└── migrations/                 # Alembic 数据库迁移
```

## 架构流程

```
Tiger WebSocket + 轮询 → Collector → Redis:raw_flows
  → Processor(评分+AI) → Redis:scored_flows + PostgreSQL
  → FastAPI(REST+WS) → Next.js 前端
  → Celery → 微信推送
```

## 验证

1. 访问 http://localhost:8000/docs 确认 API 正常
2. 美股交易时段查看 Redis：`redis-cli xlen raw_flows`
3. 查询数据库：`SELECT COUNT(*), MAX(score) FROM option_flows WHERE timestamp > NOW()-INTERVAL '1h'`
4. 浏览器访问 http://localhost:3000 验证实时更新

## 安全事项

- `tiger_openapi_config.properties` 已加入 `.gitignore`
- 私钥通过 Docker volume 挂载，不打入镜像
- 所有 AI 输出包含免责声明：⚠️仅供参考，不构成投资建议
- 生产环境 API 需 JWT 认证

---

*OptionFlow Pro · 内部项目*
