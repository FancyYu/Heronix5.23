"""
MindBloom 种子数据脚本
运行：python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from app.database import SessionLocal, engine, Base
from app.models import User, Status, Action, Interest, FocusSession

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ---------- 创建演示用户 ----------
demo_user = User(
    id="demo_user_001",
    name="小宁",
    communication_style="gentle",
    energy_pattern="scattered",
    sensory_sensitivity="high",
    common_challenges=["adhd", "anxiety"],
    preferred_reminders="gentle",
    motivation_triggers="curiosity",
    notes="黑客松演示用户：需要温和陪伴 + 执行功能支持",
)
db.add(demo_user)
db.flush()

uid = demo_user.id

# ---------- 状态记录 ----------
now = datetime.utcnow()
statuses_data = [
    Status(user_id=uid, recorded_at=now - timedelta(hours=3), energy_level=7, mood="happy", focus_level=6, sensory_load="comfortable", context="work"),
    Status(user_id=uid, recorded_at=now - timedelta(hours=2), energy_level=4, mood="anxious", focus_level=3, sensory_load="over", context="work"),
    Status(user_id=uid, recorded_at=now - timedelta(hours=1), energy_level=3, mood="overwhelmed", focus_level=2, sensory_load="over", context="alone"),
]
for s in statuses_data:
    db.add(s)

# ---------- 兴趣记录 ----------
interests_data = [
    Interest(user_id=uid, category="hobby", name="涂鸦/绘画", description="随手画一些简单的涂鸦，不需要很完美", energy_cost=3, engagement_level=7, pattern="sporadic", tags=["创意", "低门槛"]),
    Interest(user_id=uid, category="hobby", name="听播客", description="听一些轻松的知识类或故事类播客", energy_cost=2, engagement_level=8, pattern="consistent", tags=["听觉", "轻松"]),
    Interest(user_id=uid, category="skill", name="Python 小项目", description="做一些有趣的小项目，比如自动生成图片", energy_cost=6, engagement_level=6, pattern="dormant", tags=["编程", "创造"]),
    Interest(user_id=uid, category="curiosity", name="天文/宇宙", description="看天文科普视频或文章", energy_cost=4, engagement_level=9, pattern="hyperfocus", tags=["科学", "视觉"]),
    Interest(user_id=uid, category="motivation", name="运动/拉伸", description="简单的拉伸或散步", energy_cost=3, engagement_level=4, pattern="sporadic", tags=["身体", "恢复"]),
]
for i in interests_data:
    db.add(i)

# ---------- 行为记录 ----------
actions_data = [
    Action(user_id=uid, agent_type="initiate", action_type="task_breakdown", content="拆解了'写项目文档'任务为5个小步骤", status="completed"),
    Action(user_id=uid, agent_type="focus", action_type="focus_session", content="完成了1个15分钟的番茄专注", status="completed"),
    Action(user_id=uid, agent_type="explore", action_type="exploration", content="探索了'天文/宇宙'兴趣，看了10分钟科普视频", status="completed"),
]
for a in actions_data:
    db.add(a)

# ---------- 专注会话 ----------
focus_data = [
    FocusSession(user_id=uid, started_at=now - timedelta(hours=4), duration_min=15, actual_min=12, presets_used="15", completed=False, interruptions=2, focus_rating=6, note="开始不错，后来走神了"),
    FocusSession(user_id=uid, started_at=now - timedelta(hours=6), duration_min=25, actual_min=25, presets_used="25", completed=True, interruptions=1, focus_rating=8, note="状态不错，完成了任务"),
]
for f in focus_data:
    db.add(f)

db.commit()
db.close()

print("✅ 种子数据创建成功！")
print(f"   用户 ID: {uid}")
print(f"   状态: 3 条")
print(f"   兴趣: {len(interests_data)} 条")
print(f"   行为: {len(actions_data)} 条")
print(f"   专注: {len(focus_data)} 条")
print()
print(f"访问方式：")
print(f"   GET  http://localhost:8000/users/{uid}")
print(f"   GET  http://localhost:8000/users/{uid}/status/latest")
print(f"   GET  http://localhost:8000/users/{uid}/actions/recent")
print(f"   GET  http://localhost:8000/users/{uid}/interests")
print(f"   GET  http://localhost:8000/users/{uid}/focus_sessions/recent")