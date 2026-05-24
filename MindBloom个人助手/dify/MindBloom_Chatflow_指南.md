# MindBloom · Dify Chatflow 配置指南

本文档说明如何在 Dify 平台上手动搭建 MindBloom 的 Chatflow。
你可以选择先尝试导入 `MindBloom_Chatflow.yaml`，如果导入成功则跳过手动配置。

---

## 一、准备工作

### 1.1 确保后端已启动

```bash
cd backend && source venv/bin/activate && python run.py
# 服务运行在 http://localhost:8000
```

### 1.2 确认模型配置

在 Dify 的「设置 → 模型供应商」中添加：

| 字段 | 值 |
|------|----|
| 供应商 | OpenAI API Compatible |
| 模型名称 | deepseek-chat |
| API Key | 你的 DeepSeek/Anthropic/OpenAI Key |
| API Base URL | https://api.deepseek.com/v1（或其他） |

### 1.3 准备知识库

在 Dify 的「知识库」中分别导入以下文件：

| 知识库名称 | 对应文件 |
|-----------|---------|
| 神经多样性基础 | `knowledge_base/神经多样性基础.md` |
| 心理学与认知模型 | `knowledge_base/心理学与认知模型.md` |
| 行动力提升方法 | `knowledge_base/行动力提升方法.md` |
| 注意力管理方法 | `knowledge_base/注意力管理方法.md` |

导入设置：选择「文本分段」，分段长度 500，重叠 50。

---

## 二、Chatflow 节点配置（手动搭建版）

你也可以在 Dify 中直接导入 `MindBloom_Chatflow.yaml`。
如果导入异常，按以下步骤手动搭建。

### 2.1 创建 Chatflow

1. 在 Dify 工作室 → 创建应用 → Chatflow
2. 命名为 `MindBloom Agent`，图标 🧠

### 2.2 配置会话变量

在 Chatflow 的「对话变量」区域设置：

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `user_id` | 文本 | 用户唯一标识 |
| `user_profile` | JSON | 用户画像缓存 |
| `current_status` | JSON | 当前状态缓存 |
| `chat_history_summary` | 文本 | 历史会话摘要（可选） |

### 2.3 开始节点

开始节点的输入变量：

| 变量 | 类型 | 说明 |
|------|------|------|
| `sys_user_id` | 文本 | 从端传入的用户 ID |
| `sys_current_task` | 文本（可选） | 用户当前在做的任务 |

### 2.4 节点顺序

按以下顺序添加节点（共 13+ 个）：

```
开始 → 变量赋值 → HTTP(加载用户) → HTTP(加载状态) → LLM(意图识别) → 
Switch(路由) → 
  ├─ explore:    LLM(探索Agent) → HTTP(记探索行为) → HTTP(更新状态) → Answer
  ├─ initiate:   LLM(启动Agent) → HTTP(记启动行为) → HTTP(更新状态) → Answer
  ├─ focus:      LLM(专注Agent) → HTTP(记专注行为) → HTTP(更新状态) → Answer
  ├─ crisis:     Code(安全回复) → HTTP(记危机事件) → Answer
  └─ default:    Answer(默认回复)
```

---

## 三、详细节点参数

### 3.1 HTTP Request：加载用户画像

| 参数 | 值 |
|------|----|
| 方法 | GET |
| URL | `http://localhost:8000/users/{{sys_user_id}}` |
| 鉴权 | 无 |
| 超时 | 5000ms |
| 输出变量 | `user_profile`（自动） |

### 3.2 HTTP Request：加载当前状态

| 参数 | 值 |
|------|----|
| 方法 | GET |
| URL | `http://localhost:8000/status/{{sys_user_id}}/latest` |
| 鉴权 | 无 |
| 超时 | 5000ms |
| 输出变量 | `current_status`（自动） |

### 3.3 LLM：意图识别 Agent

| 参数 | 值 |
|------|----|
| 模型 | deepseek-chat |
| Temperature | 0.1 |
| Max Tokens | 64 |
| 记忆 | 不开启 |

**系统 Prompt**：见架构文档第六节「意图识别 Agent」，注意变量替换。

### 3.4 Switch 路由节点

| 条件 | 分支 |
|------|------|
| `意图识别.text` contains `explore` | → explore |
| `意图识别.text` contains `initiate` | → initiate |
| `意图识别.text` contains `focus` | → focus |
| `意图识别.text` contains `crisis` | → crisis |
| 默认 | → fallback |

### 3.5 LLM：探索 Agent

| 参数 | 值 |
|------|----|
| 模型 | deepseek-chat |
| Temperature | 0.75 |
| Max Tokens | 1024 |
| 记忆 | 开启 |
| 上下文 | `chat_history_summary` |
| 知识库 | 关联「神经多样性基础」「心理学与认知模型」 |

### 3.6 LLM：启动 Agent

| 参数 | 值 |
|------|----|
| 模型 | deepseek-chat |
| Temperature | 0.7 |
| Max Tokens | 1024 |
| 记忆 | 开启 |
| 上下文 | `chat_history_summary` |
| 知识库 | 关联「行动力提升方法」「心理学与认知模型」 |

### 3.7 LLM：专注 Agent

| 参数 | 值 |
|------|----|
| 模型 | deepseek-chat |
| Temperature | 0.7 |
| Max Tokens | 1024 |
| 记忆 | 开启 |
| 上下文 | `chat_history_summary` |
| 知识库 | 关联「注意力管理方法」「心理学与认知模型」 |

### 3.8 Code：安全降级

```python
def main(input: dict) -> dict:
    return {
        "reply": (
            "我感受到了你现在很难受。你不需要一个人面对这些。\n\n"
            "以下资源可能对你有帮助：\n"
            "• 全国24小时心理援助热线：010-82951332\n"
            "• 希望24热线（北京）：400-161-9995\n"
            "• 简单心理/安顿等APP可在线预约咨询师\n\n"
            "我不太确定我能在这件事上帮到你，但我希望你能联系专业的人。"
            "你愿意让我帮你记下来，等你状态好一些再聊别的吗？"
        )
    }
```

### 3.9 HTTP Request：记录行为

| 参数 | 值 |
|------|----|
| 方法 | POST |
| URL | `http://localhost:8000/actions` |
| 鉴权 | 无 |
| 超时 | 5000ms |

请求体（以探索为例）：

```json
{
  "user_id": "{{sys_user_id}}",
  "agent_type": "explore",
  "action_type": "exploration",
  "content": "探索对话完成",
  "status": "active"
}
```

各分支的 `agent_type` 分别为：`explore` / `initiate` / `focus` / `crisis`

### 3.10 HTTP Request：更新状态

| 参数 | 值 |
|------|----|
| 方法 | POST |
| URL | `http://localhost:8000/status` |
| 鉴权 | 无 |
| 超时 | 5000ms |

请求体：

```json
{
  "user_id": "{{sys_user_id}}",
  "energy_level": 5,
  "mood": "calm",
  "focus_level": 5,
  "sensory_load": "comfortable",
  "context": "alone"
}
```

> 实际使用时，可根据 LLM 回复中的推断来调整 energy_level 和 mood 的值。

---

## 四、前端调用方式

配置完成后，小程序/网页端通过 Dify API 调用：

```javascript
POST https://your-dify-server/v1/chat-messages
Headers:
  Authorization: Bearer {DIFY_API_KEY}
  Content-Type: application/json

Body:
{
  "inputs": {
    "sys_user_id": "demo_user_001",
    "sys_current_task": ""
  },
  "query": "我好无聊，不知道做什么",
  "response_mode": "blocking",
  "user": "demo_user_001"
}
```

---

## 五、调试建议

### 5.1 测试用例

| 输入 | 预期路由 | 说明 |
|------|---------|------|
| "我好无聊" | explore | 低能量探索 |
| "我好累，不知道要做什么" | explore | 无任务压力 |
| "周报写不出来，卡住了" | initiate | 有任务压力 |
| "帮我拆一下这个任务" | initiate | 明确启动需求 |
| "我又分心了" | focus | 注意力管理 |
| "25分钟番茄钟" | focus | 专注工具 |
| "活不下去了" | crisis | 安全降级 |

### 5.2 常见问题

| 问题 | 解决 |
|------|------|
| 意图识别不准 | 降低 Temperature 到 0.1，调整关键词 |
| 后端返回 404 | 确认 `demo_user_001` 已通过 seed.py 创建 |
| 知识库不触发 | 确认 Agent LLM 节点已关联知识库 |
| 回复太长 | 降低 Max Tokens 到 512 |
| 回复太啰嗦 | 提高 Temperature 到 0.3 |

---

## 七、小智硬件集成（在 Chatflow 中添加）

当 Agent 需要主动提醒用户时，在对应分支中添加 HTTP Request 节点。

### 在专注 Agent 分支中添加提醒

在专注 Agent 的 LLM 节点后面，添加：

| 参数 | 值 |
|------|----|
| 节点类型 | HTTP Request |
| 方法 | POST |
| URL | `http://localhost:8001/xiaozhi/remind` |
| 请求体 | `{"text": "{{{专注Agent回复}}}", "user_id": "{{sys_user_id}}", "remind_type": "focus"}` |

### 在各 Agent Prompt 末尾加入

```
## 硬件调用
当需要提醒用户时（如专注结束、任务提醒、定时关心），
调用外部 HTTP API 让小智硬件说出提醒内容。
```

---

## 八、项目文件结构

```
mindbloom/
├── backend/                    # 后端服务
│   ├── app/                    # FastAPI 应用
│   ├── seed.py                 # 种子数据
│   ├── run.py                  # 启动
│   └── requirements.txt        # 依赖
├── knowledge_base/             # Dify 知识库文档
│   ├── 神经多样性基础.md
│   ├── 心理学与认知模型.md
│   ├── 行动力提升方法.md
│   └── 注意力管理方法.md
├── dify/
│   ├── MindBloom_Chatflow.yaml # Dify Chatflow 配置（可导入）
│   └── MindBloom_Chatflow_指南.md  # 本文件
├── miniprogram/                # 微信小程序（已有）
├── config.js                   # 原有配置
└── index.html                  # 网页版（已有）
```