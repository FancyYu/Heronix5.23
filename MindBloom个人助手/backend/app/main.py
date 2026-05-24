from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import actions, focus_sessions, interests, sessions, statuses, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MindBloom API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(statuses.router)
app.include_router(actions.router)
app.include_router(interests.router)
app.include_router(focus_sessions.router)
app.include_router(sessions.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": "MindBloom"}