#!/bin/bash
cd /Users/admin/.gemini/antigravity/scratch/tradingview_bot

pkill -f "binance_bot.py" 2>/dev/null
pkill -f "streamlit" 2>/dev/null
sleep 1

echo "========================================================"
echo "🚀 Antigravity Trading Robot - Live on Mac & Mobile 🚀"
echo "========================================================"
echo "📱 Phone URL: http://192.168.1.3:8501"
echo "💻 Laptop URL: http://localhost:8501"
echo "========================================================"

# Start Bot in background
python3 binance_bot.py &

# Start Dashboard on 0.0.0.0 so phone can connect
python3 -m streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8501
