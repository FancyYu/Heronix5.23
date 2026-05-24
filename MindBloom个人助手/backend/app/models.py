import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy import JSON as SQLJSON

from app.database import Base


def gen_id():
    return str(uuid.uuid4())[:12]


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    communication_style = Column(String, default="gentle")
    energy_pattern = Column(String, default="scattered")
    sensory_sensitivity = Column(String, default="medium")
    common_challenges = Column(SQLJSON, default=list)
    preferred_reminders = Column(String, default="gentle")
    motivation_triggers = Column(String, default="curiosity")
    crisis_contact = Column(String, default="")
    notes = Column(Text, default="")


class Status(Base):
    __tablename__ = "statuses"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, index=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    energy_level = Column(Integer, default=5)
    mood = Column(String, default="calm")
    focus_level = Column(Integer, default=5)
    sensory_load = Column(String, default="comfortable")
    context = Column(String, default="alone")
    trigger_note = Column(String, default="")

    inferred_mode = Column(String, default="")
    suggestion = Column(String, default="")


class Action(Base):
    __tablename__ = "actions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent_type = Column(String)
    action_type = Column(String)
    content = Column(Text, default="")
    status = Column(String, default="active")
    completed_at = Column(DateTime, nullable=True)
    reflection = Column(Text, default="")
    sentiment = Column(String, default="")


class Interest(Base):
    __tablename__ = "interests"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = Column(String)
    name = Column(String)
    description = Column(Text, default="")
    energy_cost = Column(Integer, default=5)
    engagement_level = Column(Integer, default=5)
    last_pursued = Column(DateTime, nullable=True)
    pattern = Column(String, default="dormant")
    tags = Column(SQLJSON, default=list)


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    duration_min = Column(Integer, default=25)
    actual_min = Column(Float, default=0)
    presets_used = Column(String, default="25")
    completed = Column(Boolean, default=False)
    interruptions = Column(Integer, default=0)
    focus_rating = Column(Integer, default=5)
    note = Column(Text, default="")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    agent_path = Column(SQLJSON, default=list)
    summary = Column(Text, default="")
    key_insights = Column(SQLJSON, default=list)
    user_mood_arc = Column(SQLJSON, default=list)