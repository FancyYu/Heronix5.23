"""MindBloom Agent · 启动脚本"""
import uvicorn
from config import HOST, PORT

if __name__ == "__main__":
    print(f"  MindBloom Agent")
    print(f"  {'=' * 40}")
    print(f"  服务地址: http://{HOST}:{PORT}")
    print(f"  API 文档: http://{HOST}:{PORT}/docs")
    print(f"  健康检查: http://{HOST}:{PORT}/health")
    print(f"  {'=' * 40}")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)