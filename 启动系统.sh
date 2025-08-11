#!/bin/bash

# 推特舆情监控系统启动脚本
# 适配中文文件名

echo "🚀 启动推特舆情监控系统..."

# 检查当前目录
if [ ! -f "语义分析.py" ]; then
    echo "❌ 请在推特文件夹内运行此脚本"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查MongoDB
if ! pgrep -x "mongod" > /dev/null; then
    echo "⚠️ MongoDB 未运行，正在启动..."
    # macOS 使用 brew services
    if command -v brew &> /dev/null; then
        brew services start mongodb-community
        sleep 3
    else
        echo "请手动启动MongoDB服务"
        exit 1
    fi
fi

# 安装依赖
echo "📦 检查Python依赖..."
pip3 install -r requirements.txt > /dev/null 2>&1

# 创建日志目录
mkdir -p logs

# 检查是否已有进程在运行
if pgrep -f "自动抓取.py" > /dev/null; then
    echo "⚠️ 数据抓取进程已在运行"
else
    # 启动数据抓取进程（后台运行）
    echo "📡 启动数据抓取进程..."
    nohup python3 自动抓取.py > logs/fetch.log 2>&1 &
    FETCH_PID=$!
    echo "数据抓取进程 PID: $FETCH_PID"
fi

# 等待几秒让数据抓取开始
sleep 3

# 检查Streamlit是否已在运行
if pgrep -f "streamlit" > /dev/null; then
    echo "⚠️ Streamlit已在运行"
    echo "🌐 面板地址: http://localhost:8501"
else
    # 启动Streamlit面板
    echo "🌐 启动Streamlit可视化面板..."
    echo "面板地址: http://localhost:8501"
    echo "按 Ctrl+C 停止系统"
    
    # 启动Streamlit
    streamlit run 可视化面板.py --server.port 8501 --server.headless true
fi

# 清理函数
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    
    # 停止数据抓取进程
    pkill -f "自动抓取.py" 2>/dev/null
    
    # 停止Streamlit
    pkill -f "streamlit" 2>/dev/null
    
    echo "✅ 服务已停止"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 等待
wait