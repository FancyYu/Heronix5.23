"""MindBloom Agent 配置中心"""
import os
from dotenv import load_dotenv

load_dotenv()

# LLM 配置
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://tokendance.space/gateway/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.75"))
LLM_INTENT_TEMPERATURE = float(os.getenv("LLM_INTENT_TEMPERATURE", "0.1"))

# 后端 API 地址（已有 FastAPI 服务）
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# 小智 MCP Bridge 地址
XIAOZHI_BRIDGE_URL = os.getenv("XIAOZHI_BRIDGE_URL", "http://localhost:8001")

# 服务配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))