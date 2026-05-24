from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str = ""
    communication_style: str = "gentle"
    energy_pattern: str = "scattered"
    sensory_sensitivity: str = "medium"
    common_challenges: list[str] = []
    preferred_reminders: str = "gentle"
    motivation_triggers: str = "curiosity"
    crisis_contact: str = ""
    notes: str = ""


class UserUpdate(BaseModel):
    name: Optional[str] = None
    communication_style: Optional[str] = None
    energy_pattern: Optional[str] = None
    sensory_sensitivity: Optional[str] = None
    common_challenges: Optional[list[str]] = None
    preferred_reminders: Optional[str] = None
    motivation_triggers: Optional[str] = None
    crisis_contact: Optional[str] = None
    notes: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    communication_style: str
    energy_pattern: str
    sensory_sensitivity: str
    common_challenges: list[Any]
    preferred_reminders: str
    motivation_triggers: str
    crisis_contact: str
    notes: str

    class Config:
        from_attributes = True


class StatusCreate(BaseModel):
    user_id: str
    energy_level: int = 5
    mood: str = "calm"
    focus_level: int = 5
    sensory_load: str = "comfortable"
    context: str = "alone"
    trigger_note: str = ""
    inferred_mode: str = ""
    suggestion: str = ""


class StatusOut(BaseModel):
    id: str
    user_id: str
    recorded_at: datetime
    energy_level: int
    mood: str
    focus_level: int
    sensory_load: str
    context: str
    trigger_note: str
    inferred_mode: str
    suggestion: str

    class Config:
        from_attributes = True


class ActionCreate(BaseModel):
    user_id: str
    agent_type: str
    action_type: str
    content: str = ""
    status: str = "active"
    reflection: str = ""
    sentiment: str = ""


class ActionOut(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    agent_type: str
    action_type: str
    content: str
    status: str
    completed_at: Optional[datetime] = None
    reflection: str
    sentiment: str

    class Config:
        from_attributes = True


class InterestCreate(BaseModel):
    user_id: str
    category: str
    name: str
    description: str = ""
    energy_cost: int = 5
    engagement_level: int = 5
    pattern: str = "dormant"
    tags: list[str] = []


class InterestUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    energy_cost: Optional[int] = None
    engagement_level: Optional[int] = None
    pattern: Optional[str] = None
    tags: Optional[list[str]] = None


class InterestOut(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    category: str
    name: str
    description: str
    energy_cost: int
    engagement_level: int
    last_pursued: Optional[datetime] = None
    pattern: str
    tags: list[Any]

    class Config:
        from_attributes = True


class FocusSessionCreate(BaseModel):
    user_id: str
    duration_min: int = 25
    presets_used: str = "25"
    note: str = ""


class FocusSessionUpdate(BaseModel):
    actual_min: Optional[float] = None
    completed: Optional[bool] = None
    interruptions: Optional[int] = None
    focus_rating: Optional[int] = None
    ended_at: Optional[datetime] = None
    note: Optional[str] = None


class FocusSessionOut(BaseModel):
    id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_min: int
    actual_min: float
    presets_used: str
    completed: bool
    interruptions: int
    focus_rating: int
    note: str

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    user_id: str
    agent_path: list[str] = []
    summary: str = ""
    key_insights: list[str] = []
    user_mood_arc: list[str] = []


class SessionOut(BaseModel):
    id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    agent_path: list[Any]
    summary: str
    key_insights: list[Any]
    user_mood_arc: list[Any]

    class Config:
        from_attributes = True