# MindBloom · 个人成长助手

专为神经多样性人士设计的 AI 陪伴助手。融合意图识别 Agent、个人数据库与智能硬件（小智 AI），提供任务拆解、兴趣探索、专注支持和定时提醒。

## 在线体验

| 服务         | 地址                                                               | 状态              |
| ------------ | ------------------------------------------------------------------ | ----------------- |
| **网页前端** | **[https://mindbloom-app.loca.lt](https://mindbloom-app.loca.lt)** | ✅ 一站式前端+API |
| **本地访问** | [http://localhost:3000](http://localhost:3000)                     | 开发调试用        |

> 前端和 API 通过 proxy_server.py 合并到一个 localtunnel 隧道，无需配置 CORS。
> 演示时需要保持本地所有服务运行（详见下方快速开始）。如果隧道断开，重新运行 `npx localtunnel --port 3000` 获取新地址。

## 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                    网页端 (index.html)                           │
│         聊天界面 · 定时提醒面板 · 状态记录                      │
└──────────────┬───────────────────────┬──────────────────────────┘
               │ HTTP                    │ HTTP
               ▼                         ▼
┌──────────────────────────┐  ┌───────────────────────────────┐
│    Agent 服务 (8080)     │  │   后端 API (8000)             │
│  意图识别 → Agent 路由   │  │   FastAPI + SQLite            │
│  ┌──────┬──────┬──────┐  │  │   用户表 · 状态表 · 行为表   │
│  │探索  │启动  │专注  │  │  │   兴趣表 · 专注表 · 会话表   │
│  └──────┴──────┴──────┘  │  └───────────────────────────────┘
└──────────┬───────────────┘
           │ HTTP
           ▼
┌──────────────────────────────────────────────────────────────────┐
│               Bridge HTTP API (8001)                             │
│   工具处理函数 · 闹钟管理 · 内部分发端点                        │
│   /internal/tool/call · /mcp/create_alarm · /xiaozhi/speak      │
└──────────┬────────────────────────────────────┬─────────────────┘
           │ stdio (local_cloud_mcp.py)          │ stdio (local_stdio_mcp.py)
           ▼                                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                  xiaozhi-client (9999)                          │
│    WebSocket 连接小智云端 Broker · 聚合 MCP Server             │
│                                                                  │
│   mindbloom-cloud (8 查询工具)    mindbloom-alarm (3 闹钟工具) │
│   ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│   │ get_user_status         │  │ create_alarm                 │ │
│   │ get_user_profile        │  │ list_alarms                  │ │
│   │ get_recent_actions      │  │ delete_alarm                 │ │
│   │ get_interests           │  └──────────────────────────────┘ │
│   │ get_focus_history       │                                    │
│   │ get_context             │                                    │
│   │ create_reminder         │                                    │
│   │ get_pending_speech      │                                    │
│   └─────────────────────────┘                                    │
└──────────────────────────────────────────────────────────────────┘
           │ WebSocket (MCP 协议)
           ▼
┌──────────────────────────────────────────────────────────────────┐
│               小智云端 Broker · 小智 AI 硬件                     │
│  语音交互 · 工具发现与调用 · 设备端通信                        │
└──────────────────────────────────────────────────────────────────┘
```

### 核心设计

所有 MCP 工具统一由 xiaozhi-client 通过单一 WebSocket 连接注册到云端 Broker，避免多连接冲突。Bridge 退化为纯 HTTP API，不直接连接 Broker。

## 功能特性

### AI 对话

- **意图识别**：自动判断用户意图（探索/启动/专注/危机），路由到对应 Agent
- **探索伙伴**：帮助发现兴趣、推荐低/中/高能量活动
- **启动伙伴**：任务拆解、克服拖延、执行支持
- **专注伙伴**：番茄工作法、注意力管理、工作记忆支持
- **危机检测**：高风险情绪状态识别与求助资源引导

### 数据追踪

- 用户档案（沟通偏好、能量模式、感官敏感度）
- 状态记录（能量/情绪/专注值）
- 行为历史（Agent 交互、任务完成）
- 兴趣模式（类别、能效、参与度）
- 专注历史（时长、阶段、模式分析）

### 定时提醒

- 通过网页或小智语音创建提醒
- 到期触发 macOS 语音播报
- 同步推送至小智硬件
- Agent 主动提供待办提醒

### 小智 AI 硬件集成

- 13 个 MCP 工具注册到云端
- 查询工具：用户状态、档案、行为、兴趣、专注历史、等
- 闹钟工具：创建、查看、删除提醒

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 22+
- pnpm（安装 xiaozhi-client）

### 1. 安装项目依赖

```bash
# 后端
cd MindBloom个人助手/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py    # 初始化演示用户"小宁"

# Agent 服务
cd ../mindbloom-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Bridge（含 mcp-alarm-clock）
cd ../bridge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm install

# xiaozhi-client（全局安装）
npm install -g cnpm --registry=https://registry.npmmirror.com
cnpm install -g xiaozhi-client
```

### 2. 配置

**LLM API Key**（申请地址：https://tokendance.space/keys）

编辑 `mindbloom-agent/.env`：

```env
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://tokendance.space/gateway/v1
LLM_MODEL=deepseek-chat
```

编辑 `bridge/.env`（小智 WebSocket 接入点 Token）：

```env
XIAOZHI_WS_URL=wss://api.xiaozhi.me/mcp/?token=your-token-here
```

### 3. 创建 xiaozhi-client 项目

```bash
cd /path/to/project
xiaozhi create mindbloom-client
```

将 `mindbloom-client/xiaozhi.config.json` 内容替换为：

```json
{
  "name": "mindbloom-client",
  "mcpEndpoint": "wss://api.xiaozhi.me/mcp/?token=your-token-here",
  "mcpServers": {
    "mindbloom-cloud": {
      "command": "python3",
      "args": ["/绝对路径/bridge/local_cloud_mcp.py"]
    },
    "mindbloom-alarm": {
      "command": "python3",
      "args": ["/绝对路径/bridge/local_stdio_mcp.py"]
    }
  },
  "mcpServerConfig": {
    "mindbloom-alarm": {
      "tools": {
        "create_alarm": { "enable": true },
        "list_alarms": { "enable": true },
        "delete_alarm": { "enable": true },
        "toggle_alarm": { "enable": false },
        "speak": { "enable": false }
      }
    }
  }
}
```

### 4. 启动所有服务

#### 方式一：一键启动

```bash
cd MindBloom个人助手/mindbloom-agent
bash start.sh
```

#### 方式二：分步启动

```bash
# 终端 1 - 后端 API
cd MindBloom个人助手/backend
source venv/bin/activate
python run.py

# 终端 2 - Agent 服务
cd MindBloom个人助手/mindbloom-agent
source venv/bin/activate
python run.py

# 终端 3 - Bridge
cd MindBloom个人助手/bridge
source venv/bin/activate
python -c "
import uvicorn
uvicorn.run('main:app', host='0.0.0.0', port=8001, reload=False)
"

# 终端 4 - xiaozhi-client
cd mindbloom-client
xiaozhi start
```

### 5. 验证是否正常运行

```bash
curl -s http://localhost:8001/health
# 预期: {"status":"ok","local_alarm_clock":true,...}
```

打开 xiaozhi-client 管理界面：http://localhost:9999（应有 11 个工具已注册）

## 使用指南

### 网页端使用

打开 `MindBloom个人助手/index.html` 即可使用：

- **聊天**：输入消息，AI 自动识别意图并回复
- **定时提醒**：在提醒面板创建提醒，到期 macOS 语音播报
- **状态记录**：与 AI 对话时自动记录能量/情绪/专注状态

### 通过小智语音使用

确保 xiaozhi-client 运行中，13 个工具已注册到云端，即可对小智说话：

**查询指令示例：**

- "我的状态怎么样" → `get_context`
- "我今天做了什么" → `get_recent_actions`
- "我的兴趣有哪些" → `get_interests`
- "我的专注情况如何" → `get_focus_history`

**提醒指令示例：**

- "帮我创建提醒，10分钟后喝水" → `create_reminder`
- "列出我的所有闹钟" → `list_alarms`
- "删除我的喝水提醒" → `delete_alarm`

### API 端点

| 服务           | 端口 | 说明                |
| -------------- | ---- | ------------------- |
| 后端 API       | 8000 | 用户/状态/行为 CRUD |
| Agent API      | 8080 | 聊天/提醒/意图识别  |
| Bridge         | 8001 | 工具调度/闹钟管理   |
| xiaozhi-client | 9999 | MCP 聚合/工具管理   |

**Bridge 关键端点：**

- `GET /health` — 健康检查
- `POST /xiaozhi/speak` — 让小智说话
- `POST /xiaozhi/remind` — 推送提醒
- `POST /xiaozhi/input` — 小智输入 → Agent 处理
- `GET /alarm_clock/status` — 闹钟状态
- `POST /internal/tool/call` — 工具调用分发
- `POST /mcp/create_alarm` — 创建本地闹钟
- `GET /mcp/list_alarms` — 列出闹钟
- `POST /mcp/delete_alarm` — 删除闹钟

## 项目结构

```
项目根目录/
├── MindBloom个人助手/
│   ├── backend/                   后端 FastAPI + SQLite
│   │   ├── app/
│   │   │   ├── main.py            FastAPI 应用入口
│   │   │   ├── models.py          数据模型（6 张表）
│   │   │   ├── database.py        数据库连接
│   │   │   ├── schemas.py         Pydantic 模型
│   │   │   └── routers/           路由模块
│   │   ├── run.py                 启动脚本
│   │   ├── seed.py                演示数据初始化
│   │   └── mindbloom.db           SQLite 数据库
│   │
│   ├── mindbloom-agent/           AI Agent 服务
│   │   ├── server.py              主服务（聊天/提醒/调度）
│   │   ├── intent.py              意图识别
│   │   ├── llm.py                 LLM 调用封装
│   │   ├── config.py              配置中心
│   │   ├── agents/
│   │   │   ├── explore.py         探索 Agent
│   │   │   ├── initiate.py        启动 Agent
│   │   │   └── focus.py           专注 Agent
│   │   ├── run.py                 uvicorn 启动
│   │   └── start.sh               一键启动脚本
│   │
│   ├── bridge/                    MCP Bridge HTTP API
│   │   ├── main.py                主服务（工具处理/闹钟管理）
│   │   ├── alarm_clock.py         本地闹钟管理器
│   │   ├── local_cloud_mcp.py     云端查询工具 stdio MCP
│   │   ├── local_stdio_mcp.py     本地闹钟工具 stdio MCP
│   │   └── requirements.txt       Python 依赖
│   │
│   ├── index.html                 网页前端
│   ├── config.js                  前端配置文件
│   └── README.md                  本文档
│
└── mindbloom-client/              xiaozhi-client 项目
    └── xiaozhi.config.json        MCP Server 配置
```

## 数据模型

### 6 张核心表

| 表名             | 说明     | 关键字段                                                           |
| ---------------- | -------- | ------------------------------------------------------------------ |
| `users`          | 用户档案 | id, name, communication_style, sensory_sensitivity, crisis_contact |
| `statuses`       | 状态记录 | user_id, energy_level(1-10), mood, focus_level, sensory_load       |
| `actions`        | 行为记录 | user_id, agent_type, action_type, content, status                  |
| `interests`      | 兴趣模式 | user_id, category, name, energy_cost, engagement_level             |
| `focus_sessions` | 专注历史 | user_id, duration, stage, mode, distraction_count                  |
| `sessions`       | 对话会话 | user_id, message_count, duration                                   |

### 演示用户

初始化脚本 `seed.py` 创建演示用户"小宁"（demo_user_001），包含预设状态、行为记录和兴趣模式。

## 技术栈

| 组件       | 技术                                      |
| ---------- | ----------------------------------------- |
| AI 模型    | DeepSeek V3.2（通过 Tokendance 网关调用） |
| Agent 编排 | Python FastAPI + 自研意图路由             |
| 后端       | FastAPI + SQLAlchemy + SQLite             |
| 前端       | 原生 HTML/CSS/JS（响应式，支持深色模式）  |
| MCP 协议   | JSON-RPC 2.0 over WebSocket / stdio       |
| 本地闹钟   | mcp-alarm-clock（Node.js）                |
| 智能硬件   | 小智 AI（xiaozhi.me）                     |
| 本地客户端 | xiaozhi-client（MCP 聚合）                |

## 常见问题

**Q：提醒到时间了为什么没有语音播报？**
A：确认电脑扬声器已开启且未静音。macOS `say` 命令依赖系统 TTS 引擎。

**Q：通过小智语音创建的提醒没触发？**
A：检查 `remind_at` 参数是否传递。如果小智 AI 未传时间，提醒只存数据库不创建本地闹钟。可以通过网页端查看和管理提醒。

**Q：工具调用失败怎么办？**
A：确认所有服务都在运行：`curl http://localhost:8001/health`。查看 Bridge 日志：`tail -50 /tmp/mindbloom-bridge.log`。

**Q：如何重置演示数据？**
A：删除 `backend/mindbloom.db` 然后重新运行 `python seed.py`。
