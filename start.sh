#!/bin/bash

# 定义清理函数：当收到退出信号时关闭子进程
cleanup() {
    echo -e "\n[Make Money] 正在停止前后端服务..."
    
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    echo "[Make Money] 服务已全部停止。"
    exit 0
}

# 捕获 Ctrl+C (SIGINT) 和终止信号 (SIGTERM)
trap cleanup SIGINT SIGTERM

echo "========================================="
echo "      Make Money - 本地开发环境启动      "
echo "========================================="

# 启动后端
echo "🚀 正在启动后端 (FastAPI, 端口 8000)..."
cd backend
# 使用 uv 运行 uvicorn
uv run uvicorn main:app --port 8000 --reload &
BACKEND_PID=$!
cd ..

# 启动前端
echo "🚀 正在启动前端 (Next.js, 端口 3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "========================================="
echo "✅ 服务已启动并在后台运行！"
echo "🌐 前端访问地址: http://localhost:3000"
echo "⚙️  后端 API 地址: http://localhost:8000"
echo "🛑 停止服务请按 Ctrl + C"
echo "========================================="

# 挂起主进程，等待子进程退出
wait $BACKEND_PID
wait $FRONTEND_PID
