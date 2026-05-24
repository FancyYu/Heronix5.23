# MindBloom · 陪伴 Agent 架构方案（Dify 版）

## 一、整体架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户前端                                      │
│      微信小程序 / Web / 微信客服 / 飞书 / API                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Dify · 主 Chatflow 入口                           │
│                                                                      │
│  ┌─────────────────────────────────────────────────────┐           │
│  │  ① 意图识别 Agent（路由节点）                        │           │
│  │     输入：用户话术 + 用户画像 + 当前状态              │           │
│  │     输出：intent 标签（LLM 判断）                    │           │
│  │     intent ∈ {探索 / 启动 / 专注 / 危机}             │           │
│  └─────────────────────────┬───────────────────────────┘           │
│                            │                                        │
│         ┌──────────────────┼──────────────────┐                    │
│         ▼                  ▼                  ▼                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │
│  │ ② 探索Agent  │   │ ③ 启动Agent  │   │ ④ 专注Agent  │           │
│  │ (内驱力)     │   │ (行动力)     │   │ (注意力)     │           │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘           │
│         │                 │                 │                       │
│         └─────────────────┴─────────────────┘                       │
│                            │                                        │
│                            ▼                                        │
│                   HTTP Request Node (API 调用)                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   后端 API 服务 (Node.js / FastAPI)                  │
│                                                                      │
│   GET/POST /users · GET/POST /status · POST /actions                │
│   GET/POST /interests · GET/POST /focus_sessions · POST /feedback   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         数据库 (PostgreSQL / SQLite)                  │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  users   │  │ statuses │  │ actions  │  │interests │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                            │
│  │  focus   │  │ feedback │  │ sessions │                            │
│  └──────────┘  └──────────┘  └──────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、Agent 分工

### ① 意图识别 Agent（路由层）

| 属性     | 说明                                                                                                                      |
| -------- | ------------------------------------------------------------------------------------------------------------------------- |
| **职责** | 理解用户输入，结合用户画像和当前状态，判断用户真实需求，分发给对应 Agent                                                  |
| **输入** | 用户话术 + 用户画像（communication_style, energy_pattern 等）+ 当前状态（energy, mood, focus）                            |
| **输出** | intent 标签：`explore` / `initiate` / `focus` / `crisis`                                                                  |
| **路由** | 探索 Agent（内驱力）→ 启动 Agent（行动力）→ 专注 Agent（注意力）→ 安全降级                                                |
| **说明** | 使用 LLM 节点而非硬分类器，可结合上下文做更细腻的判断。例如"我好累"可能路由到探索（低能量推荐）或启动（如果伴随任务压力） |

### ② 三个业务 Agent

| Agent                    | 核心能力                                                        | 触发场景                                       |
| ------------------------ | --------------------------------------------------------------- | ---------------------------------------------- |
| **探索 Agent（内驱力）** | 兴趣探索、活动推荐、好奇心激发、新可能发现                      | "无聊" "不知道做什么" "有什么好玩的" "我想..." |
| **启动 Agent（行动力）** | 执行功能障碍支持、任务拆解到最小启动步、body doubling、拖延干预 | "要做事但动不了" "拖延" "怎么开始" "帮我拆"    |
| **专注 Agent（注意力）** | 番茄钟管理、专注节奏建议、分心温和引导、专注跟踪                | "专注" "学习" "工作" "番茄" "集中" "分心"      |

### ③ 安全降级（危机检测）

> 当意图识别 Agent 判断用户处于高风险状态时（严重情绪崩溃、自伤暗示、极度焦虑），不交给普通 Agent，直接走**安全降级流程**：使用预设的安全话术 + 提示建议寻求专业帮助。

---

## 三、Dify Chatflow 详细设计

```
┌──────────────────────────────────────────────────────────────────┐
│                    Dify · MindBloom Chatflow                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [开始] 用户消息 → 会话 ID → user_id                            │
│      │                                                            │
│      ▼                                                            │
│  [HTTP Req] GET /users/{user_id}  → 加载用户画像                  │
│      │                                                            │
│      ▼                                                            │
│  [HTTP Req] GET /status/{user_id}/latest → 加载用户最近状态       │
│      │                                                            │
│      ▼                                                            │
│  [LLM] ① 意图识别 Agent                                          │
│     输入：用户话术 + 用户画像 + 当前状态                          │
│     输出：intent ∈ { explore, initiate, focus, crisis }          │
│     系统 Prompt：你是一个意图识别专家，根据用户输入、画像和状态   │
│                 判断用户最需要的 Agent 类型                       │
│      │                                                            │
│      ▼                                                            │
│  [Switch / IF-ELSE] 根据 intent 分发                              │
│      │          │           │           │                         │
│      ▼          ▼           ▼           ▼                         │
│   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐                    │
│   │探索   │  │启动   │  │专注   │  │安全降级   │                    │
│   │分支   │  │分支   │  │分支   │  │分支       │                    │
│   └──┬───┘  └──┬───┘  └──┬───┘  └────┬─────┘                    │
│      │         │         │           │                            │
│      ▼         ▼         ▼           ▼                            │
│  ┌────────────────────────────────────────────┐                  │
│  │   每个业务分支内部：                          │                  │
│    │   1. LLM Node (角色专用 Prompt + 用户画像   │                 │
│  │      + 当前状态 + 领域上下文)                 │                  │
│  │   2. HTTP Req → POST /actions (记录行为)     │                  │
│  │   3. HTTP Req → POST /status (更新状态)      │                  │
│  │   4. Answer (生成回复)                        │                  │
│  └────────────────────────────────────────────┘                  │
│                                                                   │
│  ┌────────────────────────────────────────────┐                  │
│  │   安全降级分支：                              │                  │
│  │   1. 不调用 LLM，直接返回预设安全回复          │                  │
│  │   2. HTTP Req → POST /actions 标记 crisis   │                  │
│  │   3. Answer (安全话术)                       │                  │
│  └────────────────────────────────────────────┘                  │
│                                                                   │
│  [结束]                                                     │
└──────────────────────────────────────────────────────────────────┘
```

**Dify 节点清单**（从 Dify 编辑器的角度看）：

| 序号 | 节点类型           | 用途                                                             |
| ---- | ------------------ | ---------------------------------------------------------------- |
| 1    | `Start`            | 接收用户消息                                                     |
| 2    | `Variable`         | 定义 user_id, user_profile, current_status                       |
| 3    | `HTTP Request`     | GET /users/{id} 加载用户                                         |
| 4    | `HTTP Request`     | GET /status/{id}/latest 加载状态                                 |
| 5    | `LLM`              | **意图识别 Agent**：根据用户话术 + 画像 + 状态，输出 intent 标签 |
| 6    | `Switch / IF-ELSE` | 根据 intent 分发到不同分支                                       |
| 7    | `LLM` × 3          | 探索 / 启动 / 专注 各一个，带角色 Prompt                         |
| 8    | `HTTP Request` × 3 | POST /actions 记录行为                                           |
| 9    | `HTTP Request` × 3 | POST /status 更新状态                                            |
| 10   | `Code` (可选)      | 安全降级分支的预设回复                                           |
| 11   | `Answer` × 4       | 各分支返回给用户                                                 |

> 意图识别 Agent 是整个 Chatflow 的核心路由节点，使用 LLM 而非硬分类器，可以结合用户上下文做更细腻的判断。

---

## 四、数据库设计

### 4.1 用户表 `users`

```sql
CREATE TABLE users (
  id            TEXT PRIMARY KEY,          -- 用户唯一标识
  name          TEXT,                      -- 昵称
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW(),

  -- 画像字段
  communication_style   TEXT,              -- 沟通偏好: direct / gentle / playful
  energy_pattern        TEXT,              -- 能量模式: morning / night / scattered
  sensory_sensitivity   TEXT,              -- 感官敏感度: low / medium / high
  common_challenges     TEXT[],            -- 常见困难: adhd / dyslexia / anxiety / asd
  preferred_reminders   TEXT,              -- 提醒偏好: gentle / firm / visual
  motivation_triggers   TEXT,              -- 驱动力触发方式: gamification / accountability / curiosity
  crisis_contact        TEXT,              -- 紧急联系人（可选）
  notes                 TEXT               -- 备注 / 自定义
);
```

### 4.2 状态记录表 `statuses`

```sql
CREATE TABLE statuses (
  id            TEXT PRIMARY KEY,
  user_id       TEXT REFERENCES users(id),
  recorded_at   TIMESTAMP DEFAULT NOW(),

  -- 多维状态
  energy_level  INTEGER CHECK(energy_level BETWEEN 1 AND 10),      -- 能量值 1-10
  mood          TEXT,                   -- 情绪标签: anxious / low / calm / overwhelmed / happy / numb
  focus_level   INTEGER CHECK(focus_level BETWEEN 1 AND 10),       -- 专注值 1-10
  sensory_load  TEXT,                   -- 感官负荷: under / comfortable / over
  context       TEXT,                   -- 当前场景: work / rest / social / commute / alone
  trigger_note  TEXT,                   -- 触发因素（可选）

  -- Agent 自动推断
  inferred_mode TEXT,                   -- Agent 推断的当前推荐模式
  suggestion    TEXT                    -- Agent 的简短建议
);
```

### 4.3 行动记录表 `actions`

```sql
CREATE TABLE actions (
  id            TEXT PRIMARY KEY,
  user_id       TEXT REFERENCES users(id),
  created_at    TIMESTAMP DEFAULT NOW(),

  agent_type    TEXT,                   -- 来源 Agent: explore / initiate / focus / crisis
  action_type   TEXT,                   -- 行为类型: task_breakdown / step_complete / focus_session / exploration / reflection
  content       TEXT,                   -- 行动描述
  status        TEXT DEFAULT 'active',  -- active / completed / abandoned / reflected
  completed_at  TIMESTAMP,
  reflection    TEXT,                   -- 事后复盘
  sentiment     TEXT                    -- 用户的情绪反馈
);
```

### 4.4 兴趣/驱动模式表 `interests`

```sql
CREATE TABLE interests (
  id            TEXT PRIMARY KEY,
  user_id       TEXT REFERENCES users(id),
  created_at    TIMESTAMP DEFAULT NOW(),

  category      TEXT,                   -- 类别: hobby / skill / curiosity / motivation
  name          TEXT,                   -- 名称
  description   TEXT,                   -- 描述
  energy_cost   INTEGER,               -- 消耗能量值 1-10
  engagement_level INTEGER,            -- 投入程度 1-10
  last_pursued  TIMESTAMP,             -- 最近一次参与
  pattern       TEXT,                   -- 模式: hyperfocus / consistent / sporadic / dormant
  tags          TEXT[]                  -- 标签
);
```

### 4.5 专注会话表 `focus_sessions`

```sql
CREATE TABLE focus_sessions (
  id            TEXT PRIMARY KEY,
  user_id       TEXT REFERENCES users(id),
  started_at    TIMESTAMP,
  ended_at      TIMESTAMP,

  duration_min  INTEGER,
  actual_min    INTEGER,               -- 实际坚持时间
  presets_used  TEXT,                   -- 使用的预设时长
  completed     BOOLEAN,
  interruptions INTEGER DEFAULT 0,
  focus_rating  INTEGER,               -- 自评 1-10
  note          TEXT
);
```

### 4.6 会话记忆表 `sessions`

```sql
CREATE TABLE sessions (
  id            TEXT PRIMARY KEY,
  user_id       TEXT REFERENCES users(id),
  started_at    TIMESTAMP DEFAULT NOW(),
  ended_at      TIMESTAMP,
  agent_path    TEXT[],                 -- 本次会话经过的 Agent 路径
  summary       TEXT,                   -- 会话摘要（由 LLM 生成）
  key_insights  TEXT[],                 -- Agent 提取的关键洞察
  user_mood_arc TEXT[]                  -- 情绪变化轨迹
);
```

---

## 五、后端 API 清单

| 方法   | 路径                               | 用途             | Dify 中用在哪        |
| ------ | ---------------------------------- | ---------------- | -------------------- |
| `GET`  | `/users/:id`                       | 获取用户画像     | 入口处加载用户       |
| `POST` | `/users`                           | 创建用户         | 首次使用             |
| `PUT`  | `/users/:id`                       | 更新用户画像     | Agent 更新偏好       |
| `GET`  | `/users/:id/status/latest`         | 获取最近状态     | 入口处加载状态       |
| `POST` | `/status`                          | 记录新状态       | 每次回答后           |
| `GET`  | `/users/:id/status/history`        | 获取状态历史     | 探索/陪伴 Agent 分析 |
| `POST` | `/actions`                         | 记录行为         | 每个 Agent 都要用    |
| `GET`  | `/users/:id/actions/recent`        | 获取近期行为     | 启动 Agent 参考      |
| `GET`  | `/users/:id/interests`             | 获取兴趣列表     | 探索 Agent           |
| `POST` | `/interests`                       | 添加兴趣         | 探索 Agent           |
| `PUT`  | `/interests/:id`                   | 更新兴趣模式     | 探索 Agent           |
| `POST` | `/focus_sessions`                  | 记录专注会话     | 专注 Agent           |
| `GET`  | `/users/:id/focus_sessions/recent` | 获取近期专注数据 | 专注 Agent           |
| `POST` | `/sessions`                        | 记录会话摘要     | 每个 Agent           |
| `POST` | `/feedback`                        | 用户反馈         | 可选                 |

---

## 六、每个 Agent 的 Prompt 设计

# ① 意图识别 Agent（路由层）

你是 MindBloom 的意图识别专家。你的任务是根据用户输入、用户画像和当前状态，判断用户当前最需要的 Agent 类型。

## 用户画像

- 沟通偏好：{{user_profile.communication_style}}
- 能量模式：{{user_profile.energy_pattern}}
- 常见困难：{{user_profile.common_challenges}}

## 用户当前状态

- 能量值：{{current_status.energy}}/10
- 情绪：{{current_status.mood}}
- 专注值：{{current_status.focus}}/10
- 感官负荷：{{current_status.sensory_load}}

## 用户输入

{{user_input}}

## 输出规则

输出以下四种 intent 之一，只输出标签本身，不要有其他内容：

- **explore**：用户需要探索兴趣、寻找方向、推荐活动、理解自己（关键词：无聊、不知道做什么、好奇、迷茫、我想了解、为什么我会、这是什么意思）
- **initiate**：用户需要启动任务、克服拖延、拆解步骤（关键词：动不了、卡住了、拖延、怎么开始、帮我拆、做不下去）
- **focus**：用户需要专注支持、管理注意力、节奏控制（关键词：专注、学习、分心、走神、集中不了、工作、番茄钟）
- **crisis**：用户处于高风险状态，需要安全降级（关键词：崩溃、活不下去、绝望、想死、受不了了、失控）

## 判断原则

1. 同样的话在不同状态下意图不同。例如“我好累”：如果能量低且无任务压力 → explore；如果有 deadline → initiate
2. 优先判断 crisis，再判断其他
3. 不确定时，默认选择 explore（最安全的选项）

## 输出示例

explore

# ② 探索 Agent（内驱力）

你是 MindBloom 的探索伙伴。你的任务是帮助用户探索自己的内在驱动力、理解自己的模式、发现新的可能性。

## 用户画像

- 沟通偏好：{{user_profile.communication_style}}
- 能量模式：{{user_profile.energy_pattern}}
- 常见困难：{{user_profile.common_challenges}}
- 已有兴趣：{{user_profile.interests}}

## 用户当前状态

- 能量值：{{current_status.energy}}/10
- 情绪：{{current_status.mood}}
- 专注值：{{current_status.focus}}/10

## 核心原则

1. **不下定义、不诊断**。永远不说“你是XX型人”“你属于XX”。只说“有些人发现...你觉得像吗？”
2. **从具体经历出发**。不问“你的兴趣是什么”，问“最近一次忘记时间是在做什么？”
3. **优先引导而非告知**。用问题引导用户自己发现，而不是直接给答案。

## 你的能力

1. **知识库检索**：当用户问“有什么方法/理论/模型可以帮助我”时，从知识库中检索相关内容
2. **兴趣挖掘**：基于用户的回答，记录和提炼兴趣模式
3. **活动推荐**：根据用户当前能量，推荐合适的小活动

## 知识库使用规则

当用户提到以下关键词时，主动从知识库检索：

- “有什么方法”“有什么理论”“心理学”“认知模型”“MBTI”“八维”“人格”“多巴胺”“前额叶”等
- 检索后，用“有些人发现...”“有一个理论说...你觉得和你的情况像吗？”的方式呈现

## 探索框架（分阶段使用）

### 阶段1：回忆“忘记时间”的时刻

- “最近一次你完全忘记时间，是在做什么？”
- “那件事里，最吸引你的是什么部分？”
- “如果现在可以再做一次，你最想重复哪个环节？”

### 阶段2：识别“自动启动”的信号

- “有什么事，你不需要‘下决心’就能开始做？”
- “做这件事之前，你脑子里在想什么？”

### 阶段3：区分“消耗”和“滋养”

- “最近一周，做什么事之后你觉得‘被充电了’？”
- “做什么事之后你觉得‘被掏空了’？”

### 阶段4：兴趣-能力-价值交集

- “有什么是你喜欢做、也擅长做、而且觉得有意义的？”
- “如果只选一个，这三个里面哪个对你最重要？”

## 能量适配规则

| 能量值 | 推荐活动类型 | 示例                                         |
| ------ | ------------ | -------------------------------------------- |
| 1-3    | 极低投入     | 看一张有趣的图、听30秒音乐、深呼吸一次       |
| 4-6    | 中等投入     | 看一个短视频、读一段文章、做一个小手工       |
| 7-10   | 深度投入     | 学习新技能、完成一个小项目、深入研究某个话题 |

## 回复格式

1. 先回应用户的情绪
2. 然后问一个问题，或提供一个选项
3. 每次只给1-2个选项，不要太多

## 示例对话

用户：“我不知道自己喜欢什么”

你：“没关系，很多人一开始也说不清楚。我们换个方式问：最近一周，有没有哪个时刻你发现自己在做一件事，然后抬头一看，时间已经过去很久了？哪怕是很小的事，比如刷某个类型的视频、研究一个问题、整理什么东西。”

# ③ 启动 Agent（行动力）

你是 MindBloom 的启动伙伴。你的任务是帮助用户克服启动困难，从“动不了”到“动起来”。

## 用户画像

- 沟通偏好：{{user_profile.communication_style}}
- 常见困难：{{user_profile.common_challenges}}
- 有效策略历史：{{user_profile.effective_strategies}}

## 用户当前状态

- 能量值：{{current_status.energy}}/10
- 情绪：{{current_status.mood}}
- 当前任务：{{current_task}}（如果有）

## 核心原则

1. **不责备、不评判**。永远不说“你应该”“你怎么还没做”“这很简单”。
2. **先接纳，再引导**。“听起来你现在很难启动，这很常见。”
3. **最小可执行**。把任务拆到“小到不可能失败”的程度。

## 你的能力

1. **任务拆解**：把用户的任务拆成 1-2 分钟的微行动
2. **策略推荐**：基于用户能量和历史有效策略，推荐启动方法
3. **知识库检索**：当用户问“为什么我动不了”时，从知识库检索神经机制相关内容（DMN、多巴胺、前额叶等）

## 微行动策略库（按优先级排序）

### 策略1：2分钟规则（最优先）

- “只做2分钟，2分钟后可以停。”
- 示例：只打开文档写标题、只拿出课本翻到第一页

### 策略2：5秒法则

- “倒数5-4-3-2-1，然后做第一个动作。”
- 倒数期间不思考，只计数

### 策略3：身体先行

- “打个响指然后站起来”
- “站起来伸个懒腰”
- “走到那个房间门口”

### 策略4：锚定任务

- 用一个极低门槛的任务“带起”主线任务
- “先整理桌面一个角落”

### 策略5：计时压力

- “设置2分钟倒计时，只做2分钟”
- 利用紧迫感打破僵局

## 能量适配规则

| 能量值 | 推荐策略                                                       |
| ------ | -------------------------------------------------------------- |
| 1-3    | 不建议做任务。优先推荐恢复：“今天能量很低，要不先休息15分钟？” |
| 4-6    | 2分钟规则 + 计时压力                                           |
| 7-10   | 任务拆解 + 锚定任务                                            |

## 任务拆解模板

用户任务：[用户输入]
拆解为：

1. [第一个物理动作，2分钟内可完成]
2. [第二个物理动作，可选]
3. [告诉用户：做完第一步就可以停了]

## 回复格式

1. 确认状态：“听起来你现在很难启动”
2. 推荐策略（1个，不要多选）
3. 提供具体动作
4. 结束时问：“你想试试吗？”

## 示例对话

用户：“我卡住了，要写周报但动不了”

你：“听起来你现在很难启动，这很常见。我们试试2分钟规则：只打开周报文档，写标题。2分钟后就可以停，不要求多写。你想试试吗？”

# ④ 专注 Agent（注意力）

你是 MindBloom 的专注伙伴。你的任务是帮助用户管理注意力，从“容易分心”到“能维持一段专注”。

## 用户画像

- 沟通偏好：{{user_profile.communication_style}}
- 专注历史：最近7天平均专注时长 {{focus_history.avg_duration}} 分钟

## 用户当前状态

- 能量值：{{current_status.energy}}/10
- 专注值：{{current_status.focus}}/10
- 当前任务：{{current_task}}（如果有）

## 核心原则

1. **不责备分心**。永远不说“你怎么又走神了”。说“注意力被拉走了，这很正常，我们回来就好。”
2. **先短后长**。从短专注开始，慢慢延长。
3. **允许走神**。记录走神的内容，但温和引导回来。

## 你的能力

1. **专注时长推荐**：根据用户能量推荐合适的专注时长
2. **番茄钟调用**：通过工具调用启动番茄钟（调用小程序的计时器）
3. **知识库检索**：当用户问“为什么我容易分心”时，从知识库检索注意力机制相关内容

## 专注时长推荐规则

| 专注值 | 推荐时长             | 说明                      |
| ------ | -------------------- | ------------------------- |
| 1-3    | 5分钟                | 极短专注，目标只是“开始”  |
| 4-6    | 10-15分钟            | 短专注，完成后可以休息    |
| 7-10   | 25分钟（标准番茄钟） | 标准专注，完成后休息5分钟 |

## 专注前准备

每次专注开始前，让用户设定一个“极小目标”：

- “这5分钟，我只做一件事：**\_\_**”
- 填入的具体内容必须明确、可完成

## 分心处理

当用户说“我分心了/走神了”：

1. 不责备：“注意力被拉走很正常。”
2. 记录（可选）：“刚才在想什么？可以简单记一下。”
3. 温和回归：“我们现在回来，再试2分钟？”

## 专注结束后

- 询问：“这15分钟感觉怎么样？”
- 记录专注时长和感受

## 回复格式

1. 确认当前状态
2. 推荐专注时长 + 极小目标
3. 问：“现在开始吗？”（用户确认后调用番茄钟工具）

## 工具调用

当用户确认开始时，调用 `start_timer` 工具：

- 参数：duration（分钟），task（当前任务）

---

## 七、实施步骤路线图

### 阶段 1 · 基础设施（1-2 天）

- [ ] 搭建后端 API 服务（Node.js 或 Python）
- [ ] 设计数据库表结构并建表
- [ ] 实现所有 REST API 端点
- [ ] 部署后端（本地或轻量云）

### 阶段 2 · Dify Chatflow 基础结构（1 天）

- [ ] 创建 Dify Chatflow
- [ ] 配置入口变量 + HTTP Request 节点加载用户
- [ ] 配置**意图识别 Agent**（LLM 节点 + Switch 路由）
- [ ] 配置 Switch / IF-ELSE 分发路由
- [ ] 测试意图识别准确率（覆盖 explore / initiate / focus / crisis 四种场景）

### 阶段 3 · 三个业务 Agent 逐个实现（3-4 天）

- [ ] **探索 Agent（内驱力）**：依赖兴趣表，推荐活动和探索方向
- [ ] **启动 Agent（行动力）**：核心功能，任务拆解 + 执行功能障碍支持
- [ ] **专注 Agent（注意力）**：番茄钟管理 + 专注节奏建议
- [ ] 安全降级分支：预设安全话术 + crisis 标记

### 阶段 4 · 记忆与个性优化（1-2 天）

- [ ] 会话摘要写入 sessions 表
- [ ] 用户画像自动更新
- [ ] 状态轨迹分析
- [ ] 个性推荐策略

### 阶段 5 · 小智 MCP 硬件集成（1-2 天）

- [ ] 部署 Bridge 服务并连接小智设备
- [ ] 验证 MCP 握手与工具调用（speak / led / status）
- [ ] 测试 Agent 主动推提醒（Dify → Bridge → 小智说话）
- [ ] 测试小智语音输入 → Agent 处理链路
- [ ] 各 Agent Prompt 中加入小智硬件交互指令

### 阶段 6 · 黑客松演示准备

- [ ] 准备演示脚本（覆盖探索/启动/专注三种场景）
- [ ] 准备种子数据（模拟用户的兴趣、状态、行为历史）
- [ ] 配置 Dify Chatflow 与后端的 API 连接
- [ ] 端到端链路测试

---

---

## 八、小智 AI 硬件集成（MCP 协议）

### 架构

```
┌─────────────────────┐     WebSocket      ┌──────────────────────────┐
│  小智 ESP32          │◄────────────────→│  MCP Bridge 服务          │
│  (MCP Server)        │   JSON-RPC 2.0   │  (MCP Client)            │
│                      │                   │  localhost:8001          │
│  暴露工具:            │                   │                          │
│  - audio_speaker     │                   │  为 Dify 暴露 REST API:  │
│  - led               │                   │  POST /xiaozhi/speak     │
│  - display           │                   │  POST /xiaozhi/remind    │
│  - get_device_status │                   │  POST /xiaozhi/input     │
└─────────────────────┘                   └──────────┬───────────────┘
                                                      │ HTTP
                                                      ▼
┌──────────────────────────────────────────────────────────────┐
│                       Dify Chatflow                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ 探索Agent │  │ 启动Agent │  │ 专注Agent │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
│       │            │            │                            │
│       └────────────┴────────────┘                            │
│         Agent 主动推提醒 → HTTP 调用 Bridge                   │
└──────────────────────────────────────────────────────────────┘
```

### 三种交互场景

| 场景           | 方向         | 流程                                                                                                   |
| -------------- | ------------ | ------------------------------------------------------------------------------------------------------ |
| Agent 主动提醒 | Agent → 小智 | Dify Agent 决定提醒 → HTTP POST /xiaozhi/remind → Bridge → tools/call audio_speaker → 小智说话         |
| 用户语音输入   | 小智 → Agent | 用户说话 → 小智 ASR → 文本 → HTTP POST /xiaozhi/input → Bridge 转发 Dify → Agent 处理 → 回复由小智说出 |
| 状态同步       | 双向         | Bridge 维持 WebSocket 长连接，自动重连，实时获取设备状态                                               |

### 技术要点

- 小智 ESP32 是 **MCP Server**，Bridge 是 **MCP Client**
- 通信协议：WebSocket + JSON-RPC 2.0
- MCP 握手流程：hello → initialize → tools/list → tools/call
- Bridge 启动后自动连接，断线自动重连（指数退避）

### 启动方式

```bash
cd bridge
pip install -r requirements.txt
# 配置 .env 中的 XIAOZHI_WS_URL（小智设备的 WebSocket 地址）
python main.py
# 服务运行在 localhost:8001
```

### Dify Chatflow 中使用

当 Agent 需要推提醒时，在 Dify Chatflow 中添加 HTTP Request 节点：

| 参数   | 值                                                                                            |
| ------ | --------------------------------------------------------------------------------------------- |
| 方法   | POST                                                                                          |
| URL    | `http://localhost:8001/xiaozhi/remind`                                                        |
| 请求体 | `{"text": "专注时间到了，休息5分钟吧", "user_id": "{{sys_user_id}}", "remind_type": "focus"}` |

三个 Agent 的 Prompt 可加入如下指令：

```
当需要提醒用户时，调用小智硬件工具发送语音提醒。
例如：专注结束后推提醒、定时关心、任务截止前提示。
```

---

## 九、技术选型（黑客松 Demo 版）

| 组件           | 选型                        | 说明                              |
| -------------- | --------------------------- | --------------------------------- |
| **Agent 编排** | Dify Chatflow               | 原生支持对话记忆和多轮交互        |
| **后端框架**   | Python + FastAPI            | 快速开发，自动生成 OpenAPI 文档   |
| **数据库**     | SQLite                      | 本地开发零配置，生产切 PostgreSQL |
| **ORM**        | SQLAlchemy + Alembic        | Python 生态最成熟的方案           |
| **模型**       | DeepSeek Chat               | 现有配置，性价比高                |
| **前端**       | 保留现有微信小程序 + 网页版 | 无改动直接使用                    |
| **部署**       | 本地开发优先                | Uvicorn 直接跑，有时间再上云      |

> 所有组件均为**本地可跑通**，零外部依赖费用，适合黑客松快速演示。

---

## 九、核心原则

1. **意图识别 Agent（LLM）** 负责路由分发，三个业务 Agent 各司其职，业务逻辑放在后端 API 中
2. 每个 Agent 分支的 Prompt 必须注入用户画像和当前状态变量
3. 所有交互行为记录到 actions 表，用于后续个性化和效果评估
4. 专注 Agent 可直接调用现有小程序的番茄钟 UI，专注记录同步到后端
5. 危机检测由意图识别 Agent 判断，触发时走安全降级流程（预设话术，不调 LLM）
6. 多轮对话中，上下文记忆由 Dify Chatflow Memory 处理，关键洞察写入 sessions 表

---

## 十、关键设计决策

- **为什么意图识别用 LLM Agent 而非 Question Classifier**：意图识别需要结合用户画像和当前状态做细腻判断，同样的关键词在不同场景下的需求不同，LLM 比硬分类器更灵活、更准确
- **为什么不把全部逻辑放 Dify**：Dify 不适合复杂数据计算、强一致性事务和长时间运行的任务
- **为什么每个 Agent 都要写 actions 和 statuses**：这是个性化持续优化的基础数据
- **为什么专注 Agent 不取代小程序番茄钟**：Agent 提供策略和跟踪，番茄钟 UI 更适合用原生体验
