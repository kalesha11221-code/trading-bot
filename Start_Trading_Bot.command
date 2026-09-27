#!/bin/bash

# Navigate to the project folder
cd /Users/admin/.gemini/antigravity/scratch/tradingview_bot

echo "===================================================="
echo "🚀 Antigravity Trading Robot - Startup Sequence 🚀"
echo "===================================================="

# Kill any existing instances of the bot or dashboard to prevent conflicts
pkill -f "binance_bot.py"
pkill -f "streamlit run dashboard.py"

echo "[1/2] Starting Background AI Robot (binance_bot.py)..."
# caffeinate prevents the Mac from sleeping while the bot runs
caffeinate -i python3 binance_bot.py &

echo "[2/2] Starting Live Dashboard (dashboard.py)..."
# Run streamlit in the background and pipe output to /dev/null to keep terminal clean
streamlit run dashboard.py --server.port 8501 > /dev/null 2>&1 &

echo ""
echo "✅ Everything is running successfully!"
echo "🌐 Opening Dashboard in your browser..."
sleep 3
open http://localhost:8501

echo ""
echo "⚠️ IMPORTANT: Do NOT close this terminal window."
echo "If you want to stop the bot, just press Ctrl+C or close this window."
echo "===================================================="

# Keep the terminal window open to show it's running
wait
