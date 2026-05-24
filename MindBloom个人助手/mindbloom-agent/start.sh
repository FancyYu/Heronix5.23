#!/bin/bash
# MindBloom MVP 一键启动脚本
# 启动后端服务 (port 8000) + Agent 服务 (port 8080) + Bridge (port 8001) + xiaozhi-client (port 9999)

MINDBLOOM_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MINDBLOOM_DIR/.." && pwd)"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     🌿 MindBloom MVP 启动中...       ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── 1. 后端 FastAPI (port 8000) ──
echo "[1/4] 启动后端服务 → port 8000"
cd "$PROJECT_DIR/backend"
if [ ! -d "venv" ]; then
    echo "  ⚠️  后端虚拟环境不存在，创建中..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q
else
    source venv/bin/activate
fi
python run.py &
BACKEND_PID=$!
echo "  ✅ 后端服务已启动 (PID: $BACKEND_PID)"
sleep 2

# ── 2. Agent 服务 (port 8080) ──
echo "[2/4] 启动 Agent 服务 → port 8080"
cd "$MINDBLOOM_DIR"
if [ ! -d "venv" ]; then
    echo "  ⚠️  Agent 虚拟环境不存在，创建中..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q
else
    source venv/bin/activate
fi
python run.py &
AGENT_PID=$!
echo "  ✅ Agent 服务已启动 (PID: $AGENT_PID)"
sleep 2

# ── 3. 小智 Bridge (port 8001) ──
echo "[3/4] 启动小智 Bridge → port 8001"
cd "$PROJECT_DIR/bridge"
if [ ! -d "venv" ]; then
    echo "  ⚠️  Bridge 虚拟环境不存在，创建中..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q
else
    source venv/bin/activate
fi
if [ ! -d "node_modules" ]; then
    echo "  ⚠️  安装 mcp-alarm-clock..."
    npm install 2>/dev/null
fi
nohup python -c "
import uvicorn
uvicorn.run('main:app', host='0.0.0.0', port=8001, reload=False)
" > /tmp/mindbloom-bridge.log 2>&1 &
BRIDGE_PID=$!
echo "  ✅ Bridge 服务已启动 (PID: $BRIDGE_PID)"
sleep 4

# ── 4. xiaozhi-client (port 9999) ──
echo "[4/4] 启动 xiaozhi-client → port 9999"
source ~/.zshrc
cd "$PROJECT_DIR/mindbloom-client"
nohup xiaozhi start > /tmp/mindbloom-xiaozhiclient.log 2>&1 &
XIAOZHI_CLIENT_PID=$!
echo "  ✅ xiaozhi-client 已启动 (PID: $XIAOZHI_CLIENT_PID)"
sleep 3

# ── 就绪 ──
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   🌿 MindBloom MVP 已就绪！          ║"
echo "  ║                                      ║"
echo "  ║   后端 API     : http://localhost:8000║"
echo "  ║   Agent API    : http://localhost:8080║"
echo "  ║   小智 Bridge  : http://localhost:8001║"
echo "  ║   xiaozhi-client: http://localhost:9999║"
echo "  ║   网页端       : 打开 index.html 即可 ║"
echo "  ║                                      ║"
echo "  ║   按 Ctrl+C 停止所有服务              ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── 退出信号 ──
trap "echo ''; echo '🛑 正在关闭所有服务...'; kill $BACKEND_PID $AGENT_PID $BRIDGE_PID $XIAOZHI_CLIENT_PID 2>/dev/null; echo '✅ 已停止'; exit 0" SIGINT SIGTERM

wait