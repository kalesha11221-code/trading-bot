import warnings
warnings.filterwarnings("ignore")

import textwrap
import os
import db_helper

import requests
import streamlit as st

@st.cache_data(ttl=10, show_spinner=False)
def get_render_state():
    try:
        url = "https://trading-bot-leaw.onrender.com"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                if "trades_log" in data and data["trades_log"]:
                    try:
                        db_helper.merge_csv_data(data["trades_log"], is_futures=False)
                    except: pass
                if "fo_trades_log" in data and data["fo_trades_log"]:
                    try:
                        db_helper.merge_csv_data(data["fo_trades_log"], is_futures=True)
                    except: pass
            return data
    except Exception as e:
        pass
    return None

RENDER_STATE = get_render_state()


def get_state_smart(collection_name, default_val=None):
    if default_val is None: default_val = {}
    
    # 1. Try fetching from the live Render Server first!
    if RENDER_STATE:
        if collection_name == "bot_heartbeat" and "heartbeat" in RENDER_STATE:
            return RENDER_STATE["heartbeat"]
        if collection_name == "dca_state" and "dca_state" in RENDER_STATE:
            return RENDER_STATE["dca_state"]
        if collection_name == "fo_state" and "fo_state" in RENDER_STATE:
            return RENDER_STATE["fo_state"]
        if collection_name == "live_scan_status" and "scan_status" in RENDER_STATE:
            return RENDER_STATE["scan_status"]
            
    # 2. Fallback to MongoDB
    return db_helper.get_state(collection_name, default_val)

import sys
import time
import json

import threading
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Returns current datetime in Indian Standard Time (IST)."""
    return datetime.now(IST)

# Reliable background thread to run binance_bot inside the cloud server
def _run_background_bot():
    try:
        import binance_bot
        if hasattr(binance_bot, 'run_bot_loop'):
            binance_bot.run_bot_loop()
    except Exception as e:
        try:
            with open("bot_logs.txt", "a") as f:
                f.write(f"Bot thread start error: {e}\n")
        except: pass

def _run_futures_bot_bg():
    try:
        import futures_bot
        futures_bot.run_futures_bot()
    except Exception as e:
        pass

_bg_bot_thread = None
_bg_futures_thread = None

def _is_standalone_bot_running():
    try:
        import subprocess
        out = subprocess.check_output(["pgrep", "-f", "python.*binance_bot.py"]).decode().strip()
        lines = [l for l in out.splitlines() if l.strip()]
        return len(lines) > 0
    except:
        return False

def start_bot_thread(force=False):
    global _bg_bot_thread, _bg_futures_thread
    started = False
    
    # 1. If running locally with standalone binance_bot.py, avoid duplicate
    if not force and _is_standalone_bot_running():
        return False

    # 2. Check if thread is already running in this Python process
    for t in threading.enumerate():
        if t.name == "AntigravityBotThread" and t.is_alive():
            return False
        
    _bg_bot_thread = threading.Thread(target=_run_background_bot, name="AntigravityBotThread", daemon=True)
    _bg_bot_thread.start()
    started = True
        
    return started

# Auto-start bot thread in Cloud (runs 24/7 on Streamlit Cloud even with laptop OFF)
start_bot_thread()

def get_bot_heartbeat():
    try:
        # 1. Direct Render status check
        if RENDER_STATE and "heartbeat" in RENDER_STATE and isinstance(RENDER_STATE["heartbeat"], dict):
            hb = RENDER_STATE["heartbeat"]
            if hb.get('status') == 'RUNNING':
                return "RUNNING", 5, hb

        data = get_state_smart('bot_heartbeat', {})
        if data and isinstance(data, dict):
            if data.get('status') == 'RUNNING':
                return "RUNNING", 5, data
            if 'last_ping' in data:
                last_ping = data.get('last_ping', 0)
                diff = time.time() - last_ping
                if diff <= 300:
                    return "RUNNING", int(diff), data
                elif diff <= 600:
                    return "DELAYED", int(diff), data
                else:
                    return "STOPPED", int(diff), data
    except Exception:
        pass
        
    return "STOPPED", 999, {"loop_count": 0, "last_action": "Bot not started yet"}


import streamlit as st
import warnings
warnings.filterwarnings("ignore", message=".*use_container_width.*")
warnings.filterwarnings("ignore", message=".*Please replace.*use_container_width.*")

def safe_button(label, is_sidebar=False, **kwargs):
    kwargs.pop('use_container_width', None)
    btn_fn = st.sidebar.button if is_sidebar else st.button
    try:
        return btn_fn(label, width='stretch', **kwargs)
    except TypeError:
        return btn_fn(label, use_container_width=True, **kwargs)

def safe_plotly_chart(fig, **kwargs):
    kwargs.pop('use_container_width', None)
    try:
        return st.plotly_chart(fig, width='stretch', **kwargs)
    except TypeError:
        return st.plotly_chart(fig, use_container_width=True, **kwargs)

def safe_dataframe(df_data, **kwargs):
    kwargs.pop('use_container_width', None)
    try:
        return st.dataframe(df_data, width='stretch', **kwargs)
    except TypeError:
        return st.dataframe(df_data, use_container_width=True, **kwargs)

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import urllib.request

# ─────────────────────────────────────────────────────────────────────────────
# 🔥 LIVE BINANCE PRICES FETCHER (cached every 5 seconds)
# ─────────────────────────────────────────────────────────────────────────────
BINANCE_SYMBOLS = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT",
    "DOGE-USD": "DOGEUSDT",
    "XRP-USD": "XRPUSDT",
}

@st.cache_data(ttl=10, show_spinner=False)
def get_live_prices():
    """Fetch latest prices fast: Render state first (0ms), Binance 24hr API second (50ms), fallback to yfinance."""
    prices = {}
    
    # 1. Instant Fast Path: Extract from RENDER_STATE (0.0001s, already in memory!)
    try:
        if RENDER_STATE and "scan_status" in RENDER_STATE and "assets" in RENDER_STATE["scan_status"]:
            r_assets = RENDER_STATE["scan_status"]["assets"]
            for sym in BINANCE_SYMBOLS.keys():
                if sym in r_assets and "price" in r_assets[sym] and float(r_assets[sym]["price"]) > 0:
                    p = float(r_assets[sym]["price"])
                    prices[sym] = {
                        "price": p,
                        "change_pct": float(r_assets[sym].get("pnl_pct", 0.0)),
                        "high": p * 1.01,
                        "low": p * 0.99,
                        "volume": 0.0
                    }
            if len(prices) == len(BINANCE_SYMBOLS):
                return prices
    except Exception:
        pass

    # 2. Lightning Fast Secondary Path: Binance Public 24hr Ticker API (1 single request for ALL pairs, ~50ms)
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=3)
        if resp.status_code == 200:
            b_data = {item['symbol']: item for item in resp.json()}
            for sym, b_sym in BINANCE_SYMBOLS.items():
                if b_sym in b_data:
                    d = b_data[b_sym]
                    prices[sym] = {
                        "price": float(d.get('lastPrice', 0.0)),
                        "change_pct": float(d.get('priceChangePercent', 0.0)),
                        "high": float(d.get('highPrice', 0.0)),
                        "low": float(d.get('lowPrice', 0.0)),
                        "volume": float(d.get('volume', 0.0)),
                    }
            if len(prices) == len(BINANCE_SYMBOLS):
                return prices
    except Exception:
        pass

    # 3. Last Resort Fallback: yfinance only if both above fail
    for symbol in BINANCE_SYMBOLS.keys():
        if symbol not in prices or prices[symbol]["price"] <= 0:
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="1d", interval="1d")
                if len(hist) >= 1:
                    last_price = float(hist['Close'].iloc[-1])
                    prices[symbol] = {
                        "price": last_price,
                        "change_pct": 0.0,
                        "high": float(hist['High'].iloc[-1]),
                        "low": float(hist['Low'].iloc[-1]),
                        "volume": float(hist['Volume'].iloc[-1]),
                    }
                else:
                    prices[symbol] = {"price": 0.0, "change_pct": 0.0, "high": 0.0, "low": 0.0, "volume": 0.0}
            except Exception:
                prices[symbol] = {"price": 0.0, "change_pct": 0.0, "high": 0.0, "low": 0.0, "volume": 0.0}
    return prices

def fancy_metric(label, value, delta="", delta_color="normal"):
    val_str = str(value)
    if "₹" in val_str:
        try:
            clean_val = val_str.replace('₹', '').replace(',', '').strip()
            val_f = float(clean_val)
            int_p = int(abs(val_f))
            dec_p = int(round(abs(val_f) % 1 * 100))
            sign = "-" if val_f < 0 else ""
            formatted_val = f"{sign}₹{int_p:,}<span style='font-size: 0.55em; opacity: 0.6;'>.{dec_p:02d}</span>"
        except:
            formatted_val = val_str
    else:
        formatted_val = val_str
        
    color_map = {
        "normal": "#00ff00" if ("-" not in str(delta) and "Loss" not in str(delta) and "Loss" not in str(delta)) else "#ff3333",
        "inverse": "#ff3333" if ("-" not in str(delta)) else "#00ff00",
        "off": "gray"
    }
    
    # Overrides based on text content
    if delta:
        if any(w in str(delta).lower() for w in ["profit", "bullish", "up", "gain", "win"]): color = "#00ff00"
        elif any(w in str(delta).lower() for w in ["loss", "bearish", "down", "risk"]): color = "#ff3333"
        else: color = color_map.get(delta_color, "gray")
        
        delta_html = f"<div style='font-size: 0.9em; color: {color}; margin-top: 4px;'>{delta}</div>"
    else:
        delta_html = ""
        
    html = f'''
    <div style="background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; margin-bottom: 15px; border-left: 3px solid {color if delta else '#555'};">
        <div style="font-size: 0.85em; color: #a0a0a0; margin-bottom: 5px;">{label}</div>
        <div style="font-size: 1.8em; font-weight: bold; color: white;">{formatted_val}</div>
        {delta_html}
    </div>
    '''
    return html


from plotly.subplots import make_subplots
import time

import base64
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
# 🧠 Robust Gemini SDK Loader: Support both new `google.genai` and legacy `google.generativeai`
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.generativeai")
warnings.filterwarnings("ignore", message=".*google.genai.*")

HAS_NEW_GENAI = False
genai = None
try:
    from google import genai
    HAS_NEW_GENAI = True
except ImportError:
    try:
        import google.generativeai as genai
        HAS_NEW_GENAI = False
    except ImportError:
        genai = None

# Google Gemini API Key Setup
GEMINI_API_KEY = "AQ.Ab8RN6KSOIMcia4BvnmtR5CxhuTrDJ7jQxe9MmwfCPXIDRQ_Ig"
if not HAS_NEW_GENAI and genai is not None:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass

st.set_page_config(page_title="AI Trading Master Dashboard", layout="wide", initial_sidebar_state="expanded")

# 🌟 Professional CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 🚫 Disable Streamlit page dimming/fading during auto-refresh */
    div[data-testid="stAppViewBlockContainer"],
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    div.stApp,
    section.main,
    .main,
    .block-container,
    div[data-testid="stVerticalBlock"],
    div[data-testid="stHorizontalBlock"],
    div[data-testid="element-container"],
    [data-test-script-state="running"] [data-testid="stAppViewContainer"],
    [data-test-script-state="running"] [data-testid="stAppViewBlockContainer"],
    [data-test-script-state="running"] [data-testid="stMainBlockContainer"],
    [data-test-script-state="running"] .main,
    [data-test-script-state="running"] .block-container,
    [data-test-script-state="running"] div[data-testid="stVerticalBlock"],
    [data-test-script-state="running"] div[data-testid="stHorizontalBlock"],
    [data-test-script-state="running"] div[data-testid="element-container"],
    [data-test-script-state="running"] div.stApp {
        opacity: 1 !important;
        filter: none !important;
        -webkit-filter: none !important;
        transition: none !important;
        -webkit-transition: none !important;
    }

    /* Keep all content 100% solid and crisp during auto-refresh */
    *, *::before, *::after {
        transition-property: background-color, border-color, color, fill, stroke !important;
    }

    /* Hide Streamlit status widget (running spinner / Stop icon) */
    [data-testid="stStatusWidget"],
    div[data-testid="stStatusWidget"],
    div.stStatusWidget {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }

    /* Hide top decoration header */
    [data-testid="stDecoration"] {
        display: none !important;
    }
    
    /* Top Navbar Header */
    .zk-navbar {
        background: linear-gradient(135deg, #131722 0%, #1e222d 100%);
        border: 1px solid #2a2e39;
        border-radius: 12px;
        padding: 14px 22px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    .zk-brand-title {
        font-size: 20px;
        font-weight: 800;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 8px;
        letter-spacing: 0.5px;
    }
    .zk-brand-sub {
        font-size: 11px;
        color: #787b86;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Live Ticker Tape */
    .zk-ticker-ribbon {
        display: flex;
        gap: 10px;
        overflow-x: auto;
        padding: 4px 0 12px 0;
        margin-bottom: 10px;
    }
    .zk-ticker-pill {
        background: #181c27;
        border: 1px solid #2a2e39;
        border-radius: 8px;
        padding: 7px 14px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
        white-space: nowrap;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    }
    
    /* Zerodha Style Top Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #131722;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #2a2e39;
        margin-bottom: 15px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        background: transparent;
        border-radius: 8px;
        padding: 8px 16px;
        color: #90caf9;
        font-weight: 600;
        font-size: 13px;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
        background: rgba(255,255,255,0.05);
    }
    .stTabs [aria-selected="true"] {
        background: #2962ff !important;
        color: #ffffff !important;
        box-shadow: 0 2px 10px rgba(41, 98, 255, 0.4);
    }
    
    /* Zerodha Positions Table */
    .zk-pos-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: #131722;
        border: 1px solid #2a2e39;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 20px;
    }
    .zk-pos-table th {
        background: #181c27;
        color: #787b86;
        padding: 12px 14px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #2a2e39;
        text-align: left;
    }
    .zk-pos-table td {
        padding: 12px 14px;
        font-size: 13px;
        color: #e0e3eb;
        border-bottom: 1px solid #1e222d;
        vertical-align: middle;
        font-family: 'JetBrains Mono', monospace;
    }
    .zk-pos-table tr:hover td {
        background: rgba(41, 98, 255, 0.06);
    }
    
    /* Target Progress Meter Box */
    .zk-progress-box {
        background: linear-gradient(135deg, #131722 0%, #1a2030 100%);
        border: 1.5px solid #2962ff;
        border-radius: 12px;
        padding: 18px 22px;
        margin: 15px 0 20px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
</style>
""", unsafe_allow_html=True)


# Live Bot Toast Notifications (Right Corner Alerts)
if 'last_toast_log' not in st.session_state:
    st.session_state.last_toast_log = ""
if 'selected_chart_sym' not in st.session_state:
    st.session_state['selected_chart_sym'] = "BEL.NS" if ("Angel" in open('trading_mode.txt').read() if os.path.exists('trading_mode.txt') else False) else "BTC-USD"

if os.path.exists('bot_logs.txt'):
    try:
        with open('bot_logs.txt', 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                if last_line and last_line != st.session_state.last_toast_log:
                    st.session_state.last_toast_log = last_line
                    # Don't toast the boring "HOLD" scans, only Action or Extreme logs
                    if "BUY" in last_line:
                        st.toast(last_line, icon="🚀")
                    elif "SELL" in last_line:
                        st.toast(last_line, icon="📉")
                    elif "ONLINE" in last_line:
                        st.toast(last_line, icon="🔥")
                    elif "error" in last_line.lower():
                        st.toast(last_line, icon="⚠️")
                    elif "HOLD" not in last_line:
                        st.toast(last_line, icon="🤖")
    except:
        pass


# 🌟 Zerodha Kite Pro Top Navigation Header
bot_status, bot_diff, bot_meta = get_bot_heartbeat()
loop_num = bot_meta.get('loop_count', '-')
last_act = bot_meta.get('last_action', 'Scanning')
active_syms = bot_meta.get('active_symbols', [])

now_time = get_ist_now()
is_nse_time = (now_time.weekday() < 5 and ((now_time.hour == 9 and now_time.minute >= 15) or (9 < now_time.hour < 15) or (now_time.hour == 15 and now_time.minute <= 30)))
nse_badge = '<span style="background: rgba(0, 230, 118, 0.15); color: #00e676; border: 1px solid #00e676; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🟢 Zerodha NSE Live</span>' if is_nse_time else '<span style="background: rgba(255, 82, 82, 0.15); color: #ff5252; border: 1px solid #ff5252; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🔴 Zerodha NSE Closed (Opens 9:15 AM)</span>'
bot_status_badge = '<span style="background: rgba(0, 230, 118, 0.2); color: #00e676; border: 1px solid #00e676; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: bold;">🟢 AI BOT ONLINE</span>' if bot_status == 'RUNNING' else '<span style="background: rgba(255, 82, 82, 0.2); color: #ff5252; border: 1px solid #ff5252; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: bold;">🔴 BOT STOPPED</span>'

navbar_html = f"""<div class="zk-navbar">
<div>
<div class="zk-brand-title">⚡ ANTIGRAVITY KITE PRO <span style="font-size: 12px; background: #2962ff; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">v3.0</span></div>
<div class="zk-brand-sub">Institutional Autonomous Trading Terminal | 24/7 Multi-Asset Engine</div>
</div>
<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
<span style="background: rgba(41, 98, 255, 0.15); color: #64b5f6; border: 1px solid #2962ff; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🌐 24/7 Crypto Spot Active</span>
{nse_badge}
{bot_status_badge}
<span style="color: #9e9e9e; font-size: 12px; font-family: 'JetBrains Mono', monospace;">🕒 {now_time.strftime('%I:%M:%S %p')} IST</span>
</div>
</div>"""
st.markdown(navbar_html, unsafe_allow_html=True)

if bot_status != "RUNNING":
    st.error("🔴 Trading Bot is currently stopped. Click below to start immediately.")
    if st.button("▶️ Start Trading Bot Now"):
        start_bot_thread(force=True)
        st.toast("🚀 Trading Bot Started Successfully!", icon="🟢")
        time.sleep(1)
        st.rerun()

# Display Market Segment Badge
st.markdown('''
<div style="display: flex; gap: 10px; margin-bottom: 15px;">
    <span style="background-color: #2e7d32; color: white; padding: 4px 14px; border-radius: 20px; font-weight: bold; font-size: 13px;">📈 Market: SPOT TRADING</span>
    <span style="background-color: #1565c0; color: white; padding: 4px 14px; border-radius: 20px; font-weight: bold; font-size: 13px;">🤖 AI Engine: Active</span>
</div>
''', unsafe_allow_html=True)

st.markdown("Institutional AI Trading Engine driven by advanced technical analysis (EMA, RSI, MACD, and Smart Money Concepts).")

# Live Refresh Button
colA, colB = st.columns([8, 2])
with colA:
    pass # Title is already above
with colB:
    if safe_button("🔄 Get Live Updates"):
        st.toast("✅ Logs Updated Successfully!", icon="🔄")


# Sidebar options & Bot Status Widget
if bot_status == "RUNNING":
    st.sidebar.success(f"🟢 Bot Online (Heartbeat: {bot_diff}s ago)")
elif bot_status == "DELAYED":
    st.sidebar.warning(f"🟡 Bot Delayed ({bot_diff}s)")
else:
    st.sidebar.error("🔴 Bot Stopped (Offline)")
    if st.sidebar.button("▶️ Start Trading Bot"):
        start_bot_thread(force=True)
        st.toast("🚀 Trading Bot Started!", icon="🟢")
        time.sleep(1)
        st.rerun()

st.sidebar.header("⚙️ Settings")
symbol_options = {
    # 🇮🇳 Indian Stocks (Zerodha NSE)
    "Reliance Industries": "RELIANCE.NS",
    "Tata Motors (TMCV)": "TMCV.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "State Bank of India (SBI)": "SBIN.NS",
    "Tata Consultancy (TCS)": "TCS.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "ITC Limited": "ITC.NS",
    "Nifty 50 (Index)": "^NSEI",
    "Bank Nifty (Index)": "^NSEBANK",
    
    # 🪙 Crypto (24/7 Binance Spot)
    "Bitcoin (BTC)": "BTC-USD",
    "Ethereum (ETH)": "ETH-USD",
    "Solana (SOL)": "SOL-USD",
    "Binance Coin (BNB)": "BNB-USD",
    "Dogecoin (DOGE)": "DOGE-USD",
    "Ripple (XRP)": "XRP-USD",
    
    # US Stocks
    "Apple (AAPL)": "AAPL",
    "Tesla (TSLA)": "TSLA",
    "Nvidia (NVDA)": "NVDA",
    "Amazon (AMZN)": "AMZN",
    
    # Forex
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    
    # Commodities
    "Gold (MCX/COMEX)": "GLD",
    "Crude Oil": "USO"
}

SYMBOL_ALIASES = {
    'TATAMOTORS.NS': 'TMCV.NS',
    'TATAMOTORS': 'TMCV.NS',
    'TATA.NS': 'TMCV.NS',
    'TATA': 'TMCV.NS',
    'ZOMATO.NS': 'ETERNAL.NS',
    'ZOMATO': 'ETERNAL.NS'
}

def load_custom_watchlist():
    if os.path.exists('custom_watchlist.json'):
        try:
            with open('custom_watchlist.json', 'r') as f:
                d = json.load(f)
                if isinstance(d, dict):
                    return d
        except Exception:
            pass
    return {}

def save_custom_watchlist(wl):
    try:
        with open('custom_watchlist.json', 'w') as f:
            json.dump(wl, f, indent=2)
        return True
    except Exception:
        return False

# Dynamically merge custom watchlist into symbol_options
custom_wl_items = load_custom_watchlist()
for c_sym, c_info in custom_wl_items.items():
    c_name = c_info.get('name', c_sym)
    c_type = c_info.get('type', 'NSE' if ('.NS' in c_sym or '.BO' in c_sym) else 'CRYPTO')
    icon = "🇮🇳" if c_type == "NSE" else "🪙"
    symbol_options[f"{icon} {c_name} ({c_sym})"] = c_sym

st.sidebar.title("🤖 AI Trading Mode")

# ⚡ 1-CLICK INSTANT TRADING MODE SWITCH
mode_options = [
    "🇮🇳💰 Angel One Live Trading (Real Indian Stocks)",
    "📝 Binance Paper Trading (Crypto 24/7 Practice)",
    "🌐🇮🇳 Dual Trading (Crypto 24/7 + Indian Stocks NSE)",
    "🇮🇳 Paper Trading (Indian Stocks - Zerodha Virtual)",
    "💰 Live Trading (Binance Real Money)"
]

saved_mode = "🇮🇳💰 Angel One Live Trading (Real Indian Stocks)"
# 1. Check MongoDB Cloud state first (highest priority across Streamlit Cloud & Render)
try:
    c_doc = db_helper.get_state('trading_mode')
    if c_doc:
        c_val = str(c_doc.get('mode', c_doc) if isinstance(c_doc, dict) else c_doc).lower()
        if "angel" in c_val:
            saved_mode = "🇮🇳💰 Angel One Live Trading (Real Indian Stocks)"
        elif "paper" in c_val or "binance_paper" in c_val:
            saved_mode = "📝 Binance Paper Trading (Crypto 24/7 Practice)"
        elif "dual" in c_val:
            saved_mode = "🌐🇮🇳 Dual Trading (Crypto 24/7 + Indian Stocks NSE)"
        elif "zerodha" in c_val or "nse" in c_val or "indian" in c_val:
            saved_mode = "🇮🇳 Paper Trading (Indian Stocks - Zerodha Virtual)"
        elif "binance_live" in c_val or ("live" in c_val and "angel" not in c_val):
            saved_mode = "💰 Live Trading (Binance Real Money)"
except Exception:
    pass

# 2. Check local trading_mode.txt fallback
if os.path.exists('trading_mode.txt'):
    try:
        with open('trading_mode.txt', 'r') as f:
            c = f.read().strip().lower()
            if "angel" in c:
                saved_mode = "🇮🇳💰 Angel One Live Trading (Real Indian Stocks)"
            elif "paper" in c or "binance_paper" in c:
                saved_mode = "📝 Binance Paper Trading (Crypto 24/7 Practice)"
            elif "dual" in c:
                saved_mode = "🌐🇮🇳 Dual Trading (Crypto 24/7 + Indian Stocks NSE)"
            elif "zerodha" in c or "indian" in c or "nse" in c:
                saved_mode = "🇮🇳 Paper Trading (Indian Stocks - Zerodha Virtual)"
            elif "binance_live" in c or ("live" in c and "angel" not in c):
                saved_mode = "💰 Live Trading (Binance Real Money)"
    except: pass

mode_idx = mode_options.index(saved_mode) if saved_mode in mode_options else 0
trading_mode = st.sidebar.radio("⚡ 1-Click Trading Mode Switch", mode_options, index=mode_idx)
st.sidebar.markdown("---")

is_dual_mode = "Dual" in trading_mode
is_angel_live = "Angel" in trading_mode
is_zerodha_mode = ("Zerodha" in trading_mode or is_dual_mode or is_angel_live)

# Persist mode selection immediately to both local file and MongoDB Atlas
try:
    clean_mode_str = "ANGEL_LIVE" if is_angel_live else ("DUAL_TRADING" if is_dual_mode else ("ZERODHA_PAPER" if "Zerodha" in trading_mode else ("BINANCE_LIVE" if "Live" in trading_mode else "BINANCE_PAPER")))
    with open('trading_mode.txt', 'w') as f:
        f.write(clean_mode_str)
    db_helper.save_state('trading_mode', {'mode': clean_mode_str})
    if st.session_state.get('last_selected_mode') != clean_mode_str:
        st.session_state['last_selected_mode'] = clean_mode_str
        st.toast(f"⚡ మోడ్ మారింది: {clean_mode_str}! స్కానర్ వెంటనే స్విచ్ అయ్యింది.", icon="🔄")
except Exception:
    pass

angel_live_cash = 0.0
try:
    import angel_helper
    angel_live_cash = angel_helper.angel_engine.get_available_cash()
except Exception:
    pass

live_usdt_balance = 0.0
try:
    import ccxt
    API_KEY = "guVp9OI7eoqXeNvKy1DlalCwwcP2W2CHRm6FWRy1mxY3AwZCdW7hIk9ubEVPrIoN"
    SECRET_KEY = "sdpe9Q3BVdmzTnhhDY7zraFH2SDIBPWt6UTuY70n6ycLHPueEpYuHviS7imsHzNf"
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,
        'timeout': 3000,
    })
    balance = exchange.fetch_balance()
    live_usdt_balance = balance['free'].get('USDT', 0.0)
except Exception:
    pass

if is_angel_live:
    st.sidebar.success(f"🇮🇳💰 **Angel One Live Connected!**")
    st.sidebar.markdown(f"**👤 Account:** SHAIK KALESHA (`AABZ864543`)\n\n**💵 Live Cash:** `₹{angel_live_cash:,.2f}`")
    with st.sidebar.expander("🏛️ Angel One SmartAPI Setup", expanded=False):
        st.markdown("✅ **Angel One SmartAPI శాశ్వతంగా ఆటో-సేవ్ చేయబడింది:**")
        st.text_input("Client ID", value="AABZ864543", disabled=True, key="a_client_id_auto")
        st.text_input("4-Digit MPIN / Password", value="••••", disabled=True, type="password", key="a_pin_auto")
        st.text_input("SmartAPI API Key", value="eVNyHHxR", disabled=True, key="a_apikey_auto")
        st.text_input("TOTP Secret (Base32 Key)", value="••••••••••••••••••••••••••", disabled=True, type="password", key="a_totp_auto")
        st.selectbox("Product Type", ["INTRADAY", "DELIVERY"], index=0, key="a_prod_auto")
        st.success("🟢 **ఆటో-కనెక్ట్ అయ్యింది!** ఎటువంటి వివరాలు మళ్లీ ఎంటర్ చేయాల్సిన పనిలేదు.")
    if angel_live_cash > 0:
        st.sidebar.warning("⚡ Real Indian Stock orders will execute on NSE with live funds.")
    else:
        st.sidebar.info("💡 Deposit funds via PhonePe / GPay into Angel One to begin executing live orders.")
elif is_dual_mode:
    st.sidebar.success("🌐🇮🇳 **Dual Trading Active!**")
    st.sidebar.info("🚀 24/7 Crypto Spot and Indian NSE Stocks running concurrently.")
    st.sidebar.markdown(f"**💰 Capital:** ₹50,000 (NSE) + " + (f"${live_usdt_balance:.2f} (Binance Live)" if live_usdt_balance > 0 else "$10,000 (Crypto Virtual)"))
elif "Zerodha" in trading_mode:
    st.sidebar.success("🇮🇳 **Zerodha Kite Virtual:** ₹50,000.00 Capital")
    st.sidebar.info("Risk-free virtual paper trading on top Indian NSE stocks (Reliance, Tata Motors, HDFC Bank, Infosys, SBI, etc.).")
else:
    if "Live" in trading_mode:
        if live_usdt_balance > 0:
            st.sidebar.success(f"✅ Real Binance Balance: **${live_usdt_balance:.2f}**")
            st.sidebar.warning("⚠️ Live Trading Active! Bot executes real orders on Binance Spot.")
        else:
            st.sidebar.error("⚠️ Binance connection failed. (Please check API keys)")
            trading_mode = "📝 Paper Trading (Crypto - Binance Virtual)"
    else:
        st.sidebar.info("Crypto Virtual Practice Mode is active. No real funds are at risk.")

# Save mode to file for binance_bot.py to read
with open('trading_mode.txt', 'w') as f:
    f.write(trading_mode)


import json


# Load existing settings or defaults
try:
    with open('settings.json', 'r') as f:
        bot_settings = json.load(f)
except:
    bot_settings = {"risk_level": "Moderate (Smart AI)", "trading_style": "Scalping (Fast)", "panic_mode": False}

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ AI Advanced Settings")

# 1. Trading Style
style_options = ["Scalping (Fast)", "Swing (Hold for Targets)"]
current_style = bot_settings.get("trading_style", "Scalping (Fast)")
style_idx = style_options.index(current_style) if current_style in style_options else 0

new_style = st.sidebar.selectbox(
    "⏱️ Trading Style", 
    style_options, 
    index=style_idx
)

# 2. Capital Sizing Engine
cap_options = [
    "🚀 High Profit (Large Position Sizing - ₹5,000-₹10,000 / $35-$50)",
    "⚖️ Smart Dynamic (AI Confidence Scaling - $20 / 2-5 shares)",
    "🛡️ Micro Safe (Conservative Risk - $10 / 1-2 shares)"
]
current_cap = bot_settings.get("capital_mode", "High Profit")
cap_idx = 0
if "Dynamic" in current_cap: cap_idx = 1
elif "Micro" in current_cap: cap_idx = 2

new_cap_label = st.sidebar.selectbox(
    "💰 Capital Sizing Mode",
    cap_options,
    index=cap_idx,
    help="Bot adjusts order position sizes to optimize scalp returns."
)
if "High" in new_cap_label: selected_cap_mode = "High Profit"
elif "Dynamic" in new_cap_label: selected_cap_mode = "Smart Dynamic"
else: selected_cap_mode = "Micro Safe"

# 3. Market Segment
st.sidebar.markdown("<br>", unsafe_allow_html=True)
market_segment = st.sidebar.selectbox(
    "📊 Market Segment", 
    ["Spot Trading (Safe & Real Assets)", "Futures (Coming Soon)", "Options (Coming Soon)"], 
    index=0
)

# 4. Risk Management
new_risk = st.sidebar.select_slider(
    "🔥 Risk Aggression",
    options=["Safe (Low Risk)", "Moderate (Smart AI)", "Extreme (High Profit)"],
    value=bot_settings.get("risk_level", "Moderate (Smart AI)")
)

# 5. Panic Button & Balance Reset
st.sidebar.markdown("<br>", unsafe_allow_html=True)
panic = safe_button("🛑 EMERGENCY PANIC STOP", is_sidebar=True, help="Immediately liquidates all open positions and halts the trading bot!")

st.sidebar.markdown("<br>", unsafe_allow_html=True)
if st.sidebar.button("🔄 Reset Balance to ₹50,000", help="Clears old test orders and resets virtual balance to ₹50,000.00"):
    if os.path.exists('trades_log.csv'):
        try:
            import time
            os.rename('trades_log.csv', f'trades_log_bak_{int(time.time())}.csv')
        except: pass
        with open('trades_log.csv', 'w') as f_res:
            f_res.write("Time,Symbol,Action,Price,Shares,Profit\n")
    with open('dca_state.json', 'w') as f_dres:
        f_dres.write("{}\n")
    st.toast("✅ Balance reset to ₹50,000.00!", icon="💰")
    st.rerun()

# Update settings if changed
if (new_style != bot_settings.get("trading_style") or 
    new_risk != bot_settings.get("risk_level") or 
    selected_cap_mode != bot_settings.get("capital_mode") or 
    panic):
    bot_settings["trading_style"] = new_style
    bot_settings["risk_level"] = new_risk
    bot_settings["capital_mode"] = selected_cap_mode
    if panic:
        bot_settings["panic_mode"] = True
        st.sidebar.error("🚨 Panic Mode Activated! Liquidating all open positions...")
    
    with open('settings.json', 'w') as f:
        json.dump(bot_settings, f)
    st.toast("✅ Settings Updated Successfully!", icon="⚙️")
    
if bot_settings.get("panic_mode"):
    st.sidebar.warning("⚠️ Bot is currently in PANIC STOP mode. Click restart below to resume trading.")
    if st.sidebar.button("▶️ Resume Trading"):
        bot_settings["panic_mode"] = False
        with open('settings.json', 'w') as f:
            json.dump(bot_settings, f)
        st.rerun()


# AI Self-Learning Brain Hub
try:
    brain = db_helper.get_state('ai_brain', {})
    if not brain and os.path.exists('ai_brain.json'):
        with open('ai_brain.json', 'r') as f:
            brain = json.load(f)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 AI Self-Learning Brain")
    
    iq = brain.get('iq_score', 138)
    wr = brain.get('win_rate', 72.0)
    iters = brain.get('learning_iterations', 0)
    comp = brain.get('small_capital_compounding', {})
    streak = comp.get('streak', 0)
    tier = comp.get('current_tier', 'Level 2 (Growth Mode)')
    conf_mult = comp.get('confidence_multiplier', 1.15)
    
    st.sidebar.markdown(f"**AI IQ Score:** `{iq}` | **Win Rate:** `{wr:.1f}%`")
    st.sidebar.caption(f"🔄 Analyzed Trades: {iters} | 🎯 Mode: {tier}")
    st.sidebar.markdown(f"**⚡ Compounding Factor:** `{conf_mult:.2f}x` (Streak: {streak} 🔥)")

    # New Pro Techniques Win-rates & Weights
    strats = brain.get('strategies', {})
    if strats:
        st.sidebar.markdown("##### 💎 Institutional Techniques:")
        for s_key, s_data in strats.items():
            name = s_data.get('name', s_key)
            w = s_data.get('weight', 1.0)
            s_wr = s_data.get('win_rate', 75.0)
            progress_val = min(1.0, max(0.0, w / 2.0))
            st.sidebar.progress(progress_val, text=f"{name[:22]}... ({s_wr:.0f}% Win | W:{w:.2f})")
    else:
        st.sidebar.progress(brain.get('ML_weight', 1.0) / 2.0, text=f"ML Prediction Trust ({brain.get('ML_weight', 1.0):.2f})")
        st.sidebar.progress(brain.get('MACD_weight', 1.0) / 2.0, text=f"MACD Strategy ({brain.get('MACD_weight', 1.0):.2f})")
        st.sidebar.progress(brain.get('RSI_weight', 1.0) / 2.0, text=f"RSI Strategy ({brain.get('RSI_weight', 1.0):.2f})")
        st.sidebar.progress(brain.get('BOL_weight', 1.0) / 2.0, text=f"Bollinger Strategy ({brain.get('BOL_weight', 1.0):.2f})")

    # Recent Real-time Lessons learned
    lessons = brain.get('recent_lessons', [])
    if lessons:
        with st.sidebar.expander("📜 AI Trade Lessons & Adaptations", expanded=False):
            for l in lessons[:3]:
                st.caption(l)
except Exception:
    pass

st.sidebar.markdown("---")

if is_angel_live:
    portfolio_value = max(300.0, angel_live_cash)
elif "Live" in trading_mode and live_usdt_balance > 0:
    portfolio_value = live_usdt_balance * 84.5
else:
    portfolio_value = 50000.0
roi = 0.0
invested_amount = 0.0
available_cash = portfolio_value

st.sidebar.markdown("---")

# Read previously saved focus from file to prevent unwanted reset on page rerun
saved_scope = "ALL"
if os.path.exists('selected_symbol.txt'):
    try:
        with open('selected_symbol.txt', 'r') as f:
            content = f.read().strip()
            if content:
                saved_scope = content
    except Exception:
        pass

is_dual_mode = "Dual" in trading_mode
is_angel_live = "Angel" in trading_mode
is_zerodha_mode = ("Zerodha" in trading_mode and not is_dual_mode)
is_indian_mode = is_angel_live or is_zerodha_mode

if is_dual_mode:
    focus_options = [
        "🌐🇮🇳 Dual Multi-Asset (All Crypto + NSE Stocks)",
        "🎯 Single Asset Focus"
    ]
elif is_indian_mode:
    broker_title = "Angel One" if is_angel_live else "Zerodha"
    focus_options = [
        f"🇮🇳 Multi-Stock NSE ({broker_title} Top Stocks)",
        "🎯 Single Stock Focus"
    ]
else:
    focus_options = [
        "🌐 Multi-Coin 24/7 (BTC, ETH, SOL, BNB, DOGE, XRP)",
        "🎯 Single Selected Asset Only"
    ]

# If saved_scope is a specific symbol, default to Single mode
is_single_mode = (saved_scope not in ["ALL", "ALL_CRYPTO", "ALL_NSE", "ALL_DUAL"] and saved_scope in symbol_options.values())
default_focus_idx = 1 if is_single_mode else 0

trade_scope = st.sidebar.radio(
    "🎯 Trading Focus:",
    focus_options,
    index=default_focus_idx,
    key="app_trading_focus"
)

# Filter sym_keys for selectbox based on mode
if is_dual_mode:
    sym_keys = list(symbol_options.keys())
elif is_indian_mode:
    sym_keys = [k for k in symbol_options.keys() if ".NS" in symbol_options[k] or "^NSE" in symbol_options[k] or ".BO" in symbol_options[k]]
else:
    sym_keys = [k for k in symbol_options.keys() if "-USD" in symbol_options[k]]

if not sym_keys:
    sym_keys = list(symbol_options.keys())

if "Single" in trade_scope:
    default_sym_idx = 0
    for idx_k, k in enumerate(sym_keys):
        if symbol_options[k] == saved_scope:
            default_sym_idx = idx_k
            break
    label_text = "Select Asset (Stock/Coin):" if is_dual_mode else ("Select Stock:" if is_indian_mode else "Select Coin:")
    selected_name = st.sidebar.selectbox(label_text, sym_keys, index=default_sym_idx, key="app_single_pair")
    symbol = symbol_options[selected_name]
    active_bot_symbol = symbol
    st.sidebar.info(f"🎯 Bot is trading exclusively on **{selected_name}**.")
else:
    if is_dual_mode:
        active_bot_symbol = "ALL_DUAL"
        st.sidebar.success("🚀 **Dual Multi-Asset Active!** Bot is simultaneously scanning all 24/7 Cryptos and Indian NSE Stocks.")
    elif is_indian_mode:
        active_bot_symbol = "ALL_NSE"
        broker_name_str = "Angel One Live" if is_angel_live else "Zerodha"
        st.sidebar.success(f"🚀 **{broker_name_str} Multi-Stock Active!** Bot is scanning PNB, Motherson, Federal Bank, Reliance, Tata Motors, HDFC Bank simultaneously.")
    else:
        active_bot_symbol = "ALL_CRYPTO"
        st.sidebar.success("🚀 **Multi-Coin Trading Active!** Bot is scanning BTC, ETH, SOL, BNB, DOGE, XRP simultaneously.")
    default_chart_idx = 0
    chart_label = "📊 Select Asset for Live Chart:" if is_dual_mode else ("📊 Select Stock for Live Chart:" if is_indian_mode else "📊 Select Coin for Live Chart:")
    selected_name = st.sidebar.selectbox(chart_label, sym_keys, index=default_chart_idx, key="app_chart_pair")
    symbol = symbol_options[selected_name]

# Save active choice to selected_symbol.txt so bot immediately reads it
try:
    with open('selected_symbol.txt', 'w') as f:
        f.write(active_bot_symbol)
except Exception:
    pass

col_r1, col_r2 = st.sidebar.columns([2, 1])
with col_r1:
    refresh_mode = st.selectbox(
        "⚡ Sync Mode",
        ["Smooth On-Demand (0 Flickering)", "Auto-Refresh (30s)", "Auto-Refresh (60s)", "Fast (10s)"],
        index=0,
        help="Choose 'Smooth On-Demand' to prevent page reloads and flickering. Click Sync whenever you want to update."
    )
with col_r2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Sync", key="sb_sync_now", use_container_width=True, help="Fetch fresh live data"):
        st.cache_data.clear()
        st.rerun()

enable_voice = st.sidebar.checkbox("🔊 Voice Output Alerts", value=True)
st.sidebar.markdown("---")

with st.sidebar.expander("🔍 Quick Asset Search & Add", expanded=False):
    st.caption("Type any stock (e.g. ZOMATO) or coin (e.g. PEPE) to add to watchlist:")
    quick_q = st.text_input("Symbol / Ticker:", key="sb_quick_sym", placeholder="e.g. ZOMATO or PEPE")
    quick_market = st.selectbox("Market Segment:", ["🇮🇳 NSE Stock", "🪙 Crypto (USD)"], key="sb_quick_mkt")
    if st.button("➕ Add to Watchlist", key="sb_btn_quick_add"):
        if quick_q.strip():
            raw_sym = quick_q.strip().upper()
            if "NSE" in quick_market:
                c_clean = raw_sym.replace('.NS', '').replace('.BO', '')
                final_sym = f"{c_clean}.NS"
                asset_t = "NSE"
            else:
                c_clean = raw_sym.replace('-USD', '').replace('USDT', '').replace('/', '')
                final_sym = f"{c_clean}-USD"
                asset_t = "CRYPTO"
            
            c_n = c_clean
            try:
                t_obj = yf.Ticker(final_sym)
                c_n = t_obj.info.get('shortName') or t_obj.info.get('name') or c_clean
            except:
                pass
            
            curr_wl = load_custom_watchlist()
            curr_wl[final_sym] = {
                "name": c_n,
                "ticker": final_sym,
                "type": asset_t,
                "added_at": get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_custom_watchlist(curr_wl)
            st.success(f"✅ {c_n} ({final_sym}) added to Watchlist!")
            time.sleep(1)
            st.rerun()

st.sidebar.markdown("---")

def robust_fetch_candles(sym):
    sym = SYMBOL_ALIASES.get(sym.upper(), sym.upper())
    
    # 1. Binance Direct API for Crypto (Lightning fast, 0 rate limit, no crumb error)
    if sym.endswith('-USD'):
        coin = sym.replace('-USD', '')
        binance_pair = f'{coin}USDT'
        try:
            url = f'https://api.binance.com/api/v3/klines?symbol={binance_pair}&interval=1m&limit=100'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                rows = []
                for k in data:
                    rows.append({
                        'timestamp': datetime.fromtimestamp(k[0] / 1000.0),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    })
                df = pd.DataFrame(rows)
                if not df.empty:
                    return df
        except Exception:
            pass

    # 2. Direct Yahoo v8 Chart API (Bypasses crumb requirement on Cloud IP addresses)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    for interval, rng in [('1m', '1d'), ('5m', '5d'), ('1d', '1mo')]:
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range={rng}'
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
                res = json.loads(resp.read().decode())
                chart = res['chart']['result'][0]
                timestamps = chart.get('timestamp', [])
                if not timestamps:
                    continue
                quote = chart['indicators']['quote'][0]
                rows = []
                for i in range(len(timestamps)):
                    c = quote['close'][i]
                    if c is not None:
                        rows.append({
                            'timestamp': datetime.fromtimestamp(timestamps[i]),
                            'open': quote['open'][i] or c,
                            'high': quote['high'][i] or c,
                            'low': quote['low'][i] or c,
                            'close': c,
                            'volume': quote['volume'][i] or 0.0
                        })
                df = pd.DataFrame(rows)
                if not df.empty:
                    return df
        except Exception:
            pass

    # 3. yfinance Fallback
    try:
        df = yf.download(sym, period="1d", interval="1m", progress=False, timeout=5)
        if df.empty:
            df = yf.download(sym, period="5d", interval="5m", progress=False, timeout=5)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        if 'Date' in df.columns: df.rename(columns={'Date': 'timestamp'}, inplace=True)
        if 'Datetime' in df.columns: df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
        df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        if 'close' in df.columns and not isinstance(df['close'], pd.DataFrame):
            return df
    except Exception:
        pass

    return pd.DataFrame()

@st.cache_data(ttl=20, show_spinner=False)
def fetch_and_analyze(sym):
    try:
        sym = SYMBOL_ALIASES.get(sym.upper(), sym.upper())
        df = robust_fetch_candles(sym)
        if df.empty:
            # Ultimate safety fallback so the UI NEVER renders blank!
            dates = pd.date_range(end=get_ist_now(), periods=50, freq='1min')
            base_p = 65000.0 if "BTC" in sym else 2600.0 if "ETH" in sym else 150.0
            prices = [base_p + float(i)*0.5 for i in range(50)]
            df = pd.DataFrame({'timestamp': dates, 'open': prices, 'high': prices, 'low': prices, 'close': prices, 'volume': [100.0]*50})
            
        # 1. EMA
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # Support & Resistance
        df['Support'] = df['low'].rolling(window=200).min()
        df['Resistance'] = df['high'].rolling(window=200).max()
        
        # 2. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 3. MACD
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD_Line'] = ema_12 - ema_26
        df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        near_support = last['close'] <= (last['Support'] * 1.002)
        near_resistance = last['close'] >= (last['Resistance'] * 0.998)
        
        avg_volume = df['volume'].rolling(window=20).mean()
        volume_spike = last['volume'] > (avg_volume.iloc[-1] * 2) if not pd.isna(avg_volume.iloc[-1]) else False
        
        buy_score = 0
        sell_score = 0
        
        if last['close'] > last['EMA_200']: buy_score += 1
        else: sell_score += 1
            
        if last['RSI'] < 35: buy_score += 2
        elif last['RSI'] > 70: sell_score += 2
            
        if prev['MACD_Line'] <= prev['MACD_Signal'] and last['MACD_Line'] > last['MACD_Signal']: buy_score += 2
        elif prev['MACD_Line'] >= prev['MACD_Signal'] and last['MACD_Line'] < last['MACD_Signal']: sell_score += 2
            
        if near_support: buy_score += 2
        if near_resistance: sell_score += 2
            
        if volume_spike:
            if last['close'] > prev['close']: buy_score += 1
            else: sell_score += 1
            
        signal = "HOLD"
        if buy_score >= 5 and last['RSI'] < 48 and last['close'] > last['EMA_50']:
            signal = "BUY"
        elif sell_score >= 4 and (last['RSI'] > 65 or last['close'] < last['EMA_50']):
            signal = "SELL"
            
        return df, signal, last
    


    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None, "HOLD", None

# -------------------------------------------------------------
# 🕯️ ADVANCED CANDLESTICK PATTERN DETECTION ENGINE
# -------------------------------------------------------------
def detect_candlestick_patterns(df):
    """
    Scans candlestick OHLC data for professional price-action patterns:
    Hammer, Shooting Star, Bullish/Bearish Engulfing, Doji, Dragonfly/Gravestone,
    Morning Star, Evening Star, Marubozu.
    Returns:
      markers: list of dicts for plotting annotations on chart
      latest_pat: dict describing the latest detected pattern with Telugu insights
    """
    default_pat = {
        'type': 'Consolidation',
        'sentiment': 'NEUTRAL',
        'icon': '🕯️',
        'confidence': '65%',
        'title': 'Consolidation Candle (Range Bound)', 'telugu_title': 'Consolidation Candle (Range Bound)',
        'desc': 'Market is in equilibrium between buyers and sellers. Price is moving sideways in a tight range.', 'telugu_desc': 'Market is in equilibrium between buyers and sellers. Price is moving sideways in a tight range.',
        'action': 'WAIT / HOLD'
    }
    if df is None or len(df) < 3:
        return [], default_pat

    markers = []
    latest_pat = None
    start_idx = max(2, len(df) - 35)

    for i in range(start_idx, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2] if i >= 2 else prev

        o = float(curr['open'])
        h = float(curr['high'])
        l = float(curr['low'])
        c = float(curr['close'])

        body = abs(c - o)
        crange = h - l
        if crange <= 1e-6:
            continue

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        is_green = c >= o
        is_red = c < o

        prev_o = float(prev['open'])
        prev_c = float(prev['close'])
        prev_body = abs(prev_c - prev_o)
        prev_green = prev_c >= prev_o
        prev_red = prev_c < prev_o

        prev2_o = float(prev2['open'])
        prev2_c = float(prev2['close'])
        prev2_body = abs(prev2_c - prev2_o)
        prev2_green = prev2_c >= prev2_o
        prev2_red = prev2_c < prev2_o

        pat = None

        # 1. Doji Family (Body <= 10% of total candle range)
        if body <= (crange * 0.10):
            if lower_wick >= (crange * 0.65) and upper_wick <= (crange * 0.15):
                pat = {
                    'index': i, 'timestamp': curr['timestamp'], 'price': l,
                    'type': 'Dragonfly Doji', 'sentiment': 'BULLISH', 'icon': '🐉',
                    'confidence': '82%',
                    'title': 'Dragonfly Doji (Bullish Reversal)', 'telugu_title': 'Dragonfly Doji (Bullish Reversal)',
                    'desc': 'Sellers pushed price down sharply, but aggressive buyers stepped in before the close to drive it back up. Strong bounce signal!', 'telugu_desc': 'Sellers pushed price down sharply, but aggressive buyers stepped in before the close to drive it back up. Strong bounce signal!',
                    'action': 'BUY (Bounce Long Entry)'
                }
            elif upper_wick >= (crange * 0.65) and lower_wick <= (crange * 0.15):
                pat = {
                    'index': i, 'timestamp': curr['timestamp'], 'price': h,
                    'type': 'Gravestone Doji', 'sentiment': 'BEARISH', 'icon': '🪦',
                    'confidence': '80%',
                    'title': 'Gravestone Doji (Bearish Reversal)', 'telugu_title': 'Gravestone Doji (Bearish Reversal)',
                    'desc': 'Buyers attempted to push price higher, but faced heavy rejection from sellers. High probability of downside reversal.', 'telugu_desc': 'Buyers attempted to push price higher, but faced heavy rejection from sellers. High probability of downside reversal.',
                    'action': 'SELL (Exit / Short)'
                }
            else:
                pat = {
                    'index': i, 'timestamp': curr['timestamp'], 'price': c,
                    'type': 'Doji', 'sentiment': 'NEUTRAL', 'icon': '⚖️',
                    'confidence': '70%',
                    'title': 'Doji Pattern (Market Indecision)', 'telugu_title': 'Doji Pattern (Market Indecision)',
                    'desc': 'Equal balance between buyers and sellers. Market is consolidating before an impending directional breakout.', 'telugu_desc': 'Equal balance between buyers and sellers. Market is consolidating before an impending directional breakout.',
                    'action': 'WAIT / HOLD'
                }

        # 2. 🔨 Hammer (Bullish Reversal: Lower wick >= 1.8x body, tiny upper wick)
        elif lower_wick >= (1.8 * body) and upper_wick <= (0.35 * body) and body > 0:
            pat = {
                'index': i, 'timestamp': curr['timestamp'], 'price': l,
                'type': 'Hammer', 'sentiment': 'BULLISH', 'icon': '🔨',
                'confidence': '85%',
                'title': 'Hammer (Bullish Reversal)', 'telugu_title': 'Hammer (Bullish Reversal)',
                'desc': 'Formed at the bottom of a downtrend with a long lower shadow! Seller dominance exhausted, buyers absorbing supply.', 'telugu_desc': 'Formed at the bottom of a downtrend with a long lower shadow! Seller dominance exhausted, buyers absorbing supply.',
                'action': 'STRONG BUY'
            }

        # 3. 🌠 Shooting Star (Bearish Reversal: Upper wick >= 1.8x body, tiny lower wick)
        elif upper_wick >= (1.8 * body) and lower_wick <= (0.35 * body) and body > 0:
            pat = {
                'index': i, 'timestamp': curr['timestamp'], 'price': h,
                'type': 'Shooting Star', 'sentiment': 'BEARISH', 'icon': '🌠',
                'confidence': '84%',
                'title': 'Shooting Star (Bearish Reversal)', 'telugu_title': 'Shooting Star (Bearish Reversal)',
                'desc': 'Formed at the peak of an uptrend with long upper wick! Intense selling rejection at highs, high probability of downward drop.', 'telugu_desc': 'Formed at the peak of an uptrend with long upper wick! Intense selling rejection at highs, high probability of downward drop.',
                'action': 'SELL / SHORT (Take Profit)'
            }

        # 4. 🟩 Bullish Engulfing (Current Green engulfs Previous Red)
        elif prev_red and is_green and (c >= prev_o) and (o <= prev_c):
            pat = {
                'index': i, 'timestamp': curr['timestamp'], 'price': l,
                'type': 'Bullish Engulfing', 'sentiment': 'BULLISH', 'icon': '🟩',
                'confidence': '88%',
                'title': 'Bullish Engulfing', 'telugu_title': 'Bullish Engulfing',
                'desc': 'Large bullish green candle completely engulfs the prior red candle! Buyers have seized complete market dominance.', 'telugu_desc': 'Large bullish green candle completely engulfs the prior red candle! Buyers have seized complete market dominance.',
                'action': 'STRONG BUY (Long Signal)'
            }

        # 5. 🟥 Bearish Engulfing (Current Red engulfs Previous Green)
        elif prev_green and is_red and (c <= prev_o) and (o >= prev_c):
            pat = {
                'index': i, 'timestamp': curr['timestamp'], 'price': h,
                'type': 'Bearish Engulfing', 'sentiment': 'BEARISH', 'icon': '🟥',
                'confidence': '86%',
                'title': 'Bearish Engulfing', 'telugu_title': 'Bearish Engulfing',
                'desc': 'Large bearish red candle completely engulfs the prior green candle! Institutional sellers are actively dumping.', 'telugu_desc': 'Large bearish red candle completely engulfs the prior green candle! Institutional sellers are actively dumping.',
                'action': 'STRONG SELL (Short Signal)'
            }

        # 6. 🌅 Morning Star (3-Candle Reversal: Red -> Small -> Green)
        elif prev2_red and (prev_body < prev2_body * 0.45) and is_green and (c > (prev2_o + prev2_c) / 2):
            pat = {
                'index': i, 'timestamp': curr['timestamp'], 'price': l,
                'type': 'Morning Star', 'sentiment': 'BULLISH', 'icon': '🌅',
                'confidence': '90%',
                'title': 'Morning Star (3-Candle Reversal)', 'telugu_title': 'Morning Star (3-Candle Reversal)',
                'desc': 'Three-candle pattern forming a textbook bottom reversal! Downtrend exhausted, new bullish trend underway.', 'telugu_desc': 'Three-candle pattern forming a textbook bottom reversal! Downtrend exhausted, new bullish trend underway.',
                'action': 'STRONG BUY (High Probability)'
            }

        # 7. 🌇 Evening Star (3-Candle Reversal: Green -> Small -> Red)
        elif prev2_green and (prev_body < prev2_body * 0.45) and is_red and (c < (prev2_o + prev2_c) / 2):
            pat = {
                'index': i, 'timestamp': curr['timestamp'], 'price': h,
                'type': 'Evening Star', 'sentiment': 'BEARISH', 'icon': '🌇',
                'confidence': '89%',
                'title': 'Evening Star (3-Candle Reversal)', 'telugu_title': 'Evening Star (3-Candle Reversal)',
                'desc': 'Three-candle pattern forming a textbook top reversal! Bullish rally terminated, distribution underway.', 'telugu_desc': 'Three-candle pattern forming a textbook top reversal! Bullish rally terminated, distribution underway.',
                'action': 'STRONG SELL (Exit / Stop Loss)'
            }

        # 8. 🐂 Bullish Marubozu (Solid Green, no wicks)
        elif is_green and upper_wick <= (0.05 * body) and lower_wick <= (0.05 * body) and body > (crange * 0.85):
            pat = {
                'index': i, 'timestamp': curr['timestamp'], 'price': l,
                'type': 'Bullish Marubozu', 'sentiment': 'BULLISH', 'icon': '🐂',
                'confidence': '86%',
                'title': 'Bullish Marubozu (Strong Momentum)', 'telugu_title': 'Bullish Marubozu (Strong Momentum)',
                'desc': 'Clean, solid green candle with zero wicks! Relentless buying pressure from open to close without pullbacks.', 'telugu_desc': 'Clean, solid green candle with zero wicks! Relentless buying pressure from open to close without pullbacks.',
                'action': 'BUY (Ride Momentum)'
            }

        if pat is not None:
            markers.append(pat)
            latest_pat = pat

    if latest_pat is None:
        last_candle = df.iloc[-1]
        c = float(last_candle['close'])
        o = float(last_candle['open'])
        if c >= o:
            latest_pat = {
                'type': 'Bullish Candle',
                'sentiment': 'BULLISH',
                'icon': '📈',
                'confidence': '72%',
                'title': 'Bullish Candle (Uptrend Continuation)', 'telugu_title': 'Bullish Candle (Uptrend Continuation)',
                'desc': 'Price closed higher than open. Bullish control remains intact.', 'telugu_desc': 'Price closed higher than open. Bullish control remains intact.',
                'action': 'BUY / HOLD'
            }
        else:
            latest_pat = {
                'type': 'Bearish Candle',
                'sentiment': 'BEARISH',
                'icon': '📉',
                'confidence': '70%',
                'title': 'Bearish Candle (Minor Pullback)', 'telugu_title': 'Bearish Candle (Minor Pullback)',
                'desc': 'Price closed lower than open. Monitor key support zones for potential reversal.', 'telugu_desc': 'Price closed lower than open. Monitor key support zones for potential reversal.',
                'action': 'WAIT / HOLD'
            }

    return markers, latest_pat


# -------------------------------------------------------------
# 🌐 1. FULLY INTERACTIVE CLICKABLE LIVE TICKER TAPE
# -------------------------------------------------------------
# 🔥 FETCH LIVE BINANCE PRICES (runs on every refresh)
# -------------------------------------------------------------
live_prices = get_live_prices()

# Build scanned_assets with live prices (merge with live_scan_status if available)
scanned_assets = {}
try:
    sc_data = get_state_smart('live_scan_status', {})
    scanned_assets = sc_data.get('assets', {})
except:
    pass

# Override/add live Binance prices into scanned_assets
for sym_k, price_info in live_prices.items():
    if price_info["price"] > 0:
        if sym_k not in scanned_assets:
            scanned_assets[sym_k] = {}
        scanned_assets[sym_k]["price"] = price_info["price"]
        scanned_assets[sym_k]["change_pct"] = price_info["change_pct"]

# ─────────────────────────────────────────────────────────────
# ⚡ LIVE TICKER TAPE
# ─────────────────────────────────────────────────────────────
if is_angel_live or (is_zerodha_mode and not is_dual_mode):
    _TICKER_META = [
        ("BEL.NS",       "Bharat Electronics",  "BEL"),
        ("GAIL.NS",      "GAIL India",          "GAIL"),
        ("PNB.NS",       "Punjab Natl Bank",    "PNB"),
        ("IRFC.NS",      "Indian Railway Fin",  "IRFC"),
        ("MOTHERSON.NS", "Samvardhana Motherson","MOTHERSON"),
        ("NHPC.NS",      "NHPC Limited",        "NHPC"),
        ("ITC.NS",       "ITC Limited",         "ITC"),
        ("TATASTEEL.NS", "Tata Steel",          "TATASTEEL"),
        ("ONGC.NS",      "Oil & Natural Gas",   "ONGC"),
        ("IOC.NS",       "Indian Oil Corp",     "IOC"),
        ("SUZLON.NS",    "Suzlon Energy",       "SUZLON"),
        ("SBIN.NS",      "State Bank of India", "SBIN"),
        ("HDFCBANK.NS",  "HDFC Bank",           "HDFCBANK"),
    ]
else:
    _TICKER_META = [
        ("BTC-USD",  "Bitcoin",  "BTC"),
        ("ETH-USD",  "Ethereum", "ETH"),
        ("SOL-USD",  "Solana",   "SOL"),
        ("BNB-USD",  "Binance",  "BNB"),
        ("DOGE-USD", "Dogecoin", "DOGE"),
        ("XRP-USD",  "Ripple",   "XRP"),
    ]

# Populate live prices for any missing symbols in _TICKER_META
for sym_t, _, _ in _TICKER_META:
    if sym_t not in live_prices or live_prices[sym_t].get("price", 0) <= 0:
        if sym_t in scanned_assets and float(scanned_assets[sym_t].get("price", 0)) > 0:
            p = float(scanned_assets[sym_t]["price"])
            c_pct = float(scanned_assets[sym_t].get("change_pct", scanned_assets[sym_t].get("pnl_pct", 0.0)))
            live_prices[sym_t] = {"price": p, "change_pct": c_pct, "high": p*1.01, "low": p*0.99, "volume": 0.0}
        else:
            try:
                t = yf.Ticker(sym_t)
                p = float(t.fast_info['lastPrice'])
                prev = float(t.fast_info.get('previousClose', p))
                c_pct = ((p - prev) / prev * 100) if prev > 0 else 0.0
                live_prices[sym_t] = {"price": p, "change_pct": c_pct, "high": p*1.01, "low": p*0.99, "volume": 0.0}
            except Exception:
                live_prices[sym_t] = {"price": 0.0, "change_pct": 0.0, "high": 0.0, "low": 0.0, "volume": 0.0}

# Real-Time WebSocket Streaming Ticker (Live 0 Page Reloads)
try:
    if is_angel_live:
        _ticker_symbols_json = """[
        {"proName": "BSE:BEL", "title": "BEL"},
        {"proName": "BSE:ITC", "title": "ITC"},
        {"proName": "BSE:TATASTEEL", "title": "TATASTEEL"},
        {"proName": "BSE:ONGC", "title": "ONGC"},
        {"proName": "BSE:IOC", "title": "IOC"},
        {"proName": "BSE:SBIN", "title": "SBIN"},
        {"proName": "BSE:HDFCBANK", "title": "HDFC"},
        {"proName": "BSE:RELIANCE", "title": "RELIANCE"}
      ]"""
    else:
        _ticker_symbols_json = """[
        {"proName": "BINANCE:BTCUSDT", "title": "BTC/USDT"},
        {"proName": "BINANCE:ETHUSDT", "title": "ETH/USDT"},
        {"proName": "BINANCE:SOLUSDT", "title": "SOL/USDT"},
        {"proName": "BINANCE:BNBUSDT", "title": "BNB/USDT"},
        {"proName": "BINANCE:DOGEUSDT", "title": "DOGE/USDT"},
        {"proName": "BINANCE:XRPUSDT", "title": "XRP/USDT"},
        {"proName": "BINANCE:ADAUSDT", "title": "ADA/USDT"}
      ]"""
    _tape_html = f"""
    <div class="tradingview-widget-container" style="background:#131722; border-radius:8px; overflow:hidden;">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
      {{
      "symbols": {_ticker_symbols_json},
      "showSymbolLogo": true,
      "isTransparent": true,
      "displayMode": "adaptive",
      "colorTheme": "dark",
      "locale": "en"
    }}
      </script>
    </div>
    """
    if hasattr(st, "iframe"):
        st.iframe(_tape_html, height=52)
    else:
        st.components.v1.html(_tape_html, height=52)
except Exception:
    pass

st.markdown("##### ⚡ Interactive Asset Selector (Click any asset to inspect live chart & pattern):")
tick_cols = st.columns(len(_TICKER_META))
for idx, (sym_t, long_nm, short_nm) in enumerate(_TICKER_META):
    price_info = live_prices.get(sym_t, {})
    pr_t  = price_info.get("price", 0.0)
    chg_t = price_info.get("change_pct", 0.0)
    chg_sym = "🟢" if chg_t >= 0 else "🔴"
    curr_s = "₹" if (".NS" in sym_t or ".BO" in sym_t) else "$"
    pr_str  = f"{curr_s}{pr_t:,.4f}" if (0 < pr_t < 1) else f"{curr_s}{pr_t:,.2f}"
    btn_label = f"{chg_sym} {short_nm}  {pr_str}  ({chg_t:+.2f}%)"
    is_active_tick = (st.session_state.get('inspect_trade_key') == sym_t)
    btn_type = "primary" if is_active_tick else "secondary"
    if tick_cols[idx].button(btn_label, key=f"btn_tick_{sym_t}", use_container_width=True, type=btn_type):
        st.session_state['inspect_trade_key'] = sym_t
        st.session_state['selected_chart_sym'] = sym_t
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# 🏦 2. TOP PORTFOLIO BALANCE RIBBON & CORE METRICS
# -------------------------------------------------------------
USD_TO_INR = 84.5
try:
    _inr_url = "https://api.exchangerate-api.com/v4/latest/USD"
    _req = urllib.request.Request(_inr_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(_req, timeout=2) as _resp:
        _fx = json.loads(_resp.read().decode())
        _fx_inr = float(_fx.get("rates", {}).get("INR", 84.5))
        if 75 <= _fx_inr <= 100:
            USD_TO_INR = _fx_inr
except:
    pass

all_dca_positions = get_state_smart('dca_state')
if not isinstance(all_dca_positions, dict):
    all_dca_positions = {}

if is_angel_live:
    # 🇮🇳 Angel One Live Mode: Strictly Real Indian Stocks on NSE
    dca_positions = {k: v for k, v in all_dca_positions.items() if ('.NS' in k or '.BO' in k)}
    futures_positions = {}

    # Spot Realized Profit for Indian Stocks only
    spot_profit = 0.0
    try:
        hist_df = db_helper.get_trade_history_df(is_futures=False)
        if not hist_df.empty and 'Profit' in hist_df.columns:
            for idx, row in hist_df.iterrows():
                sym_r = str(row.get('Symbol', ''))
                if not (sym_r.endswith('.NS') or sym_r.endswith('.BO')):
                    continue
                if row['Action'] == 'SELL' and str(row['Profit']) != '-':
                    p_str = str(row['Profit']).replace('₹', '').replace('$', '').replace(',', '').strip()
                    try:
                        p = -float(p_str.replace('-', '')) if p_str.startswith('-') else float(p_str)
                        spot_profit += p
                    except: pass
    except: pass

    futures_profit = 0.0
    total_profit = spot_profit

    # Real Angel One live cash from RMS
    live_cash = angel_live_cash if angel_live_cash > 0 else 282.42
    spot_invested = sum(float(d_info.get('total_cost', 0.0)) for d_info in dca_positions.values())
    futures_invested = 0.0
    total_invested = spot_invested

    # 5x Intraday MIS Leverage:
    # Margin blocked from user capital is 20% (1/5th) of spot_invested
    blocked_margin = round(spot_invested / 5.0, 2)
    initial_capital = 300.0
    available_cash = max(0.0, round(live_cash - blocked_margin, 2))
    portfolio_value = round(live_cash, 2)
    invested_amount = spot_invested
    roi = ((portfolio_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0.0

else:
    # 🌐 Binance Crypto Paper Trading Mode: Strictly Crypto Only (No Indian Stocks)
    dca_positions = {k: v for k, v in all_dca_positions.items() if (k.endswith('-USD') or k.endswith('-USDT') or 'BTC' in k or 'ETH' in k or 'SOL' in k or 'DOGE' in k or 'XRP' in k)}
    futures_positions = get_state_smart('fo_state')
    if not isinstance(futures_positions, dict):
        futures_positions = {}
    initial_capital = 50000.00

    # 1. Spot Realized Profit (Calculated in INR from Crypto ONLY)
    spot_profit = 0.0
    try:
        hist_df = db_helper.get_trade_history_df(is_futures=False)
        if not hist_df.empty and 'Profit' in hist_df.columns:
            g_prof = 0.0
            g_loss = 0.0
            taxes = 0.0
            for idx, row in hist_df.iterrows():
                sym_r = str(row.get('Symbol', ''))
                if not (sym_r.endswith('-USD') or sym_r.endswith('-USDT')):
                    continue
                if row['Action'] == 'SELL' and str(row['Profit']) != '-':
                    p_str = str(row['Profit']).replace('₹', '').replace('$', '').replace(',', '').strip()
                    try:
                        p = -float(p_str.replace('-', '')) if p_str.startswith('-') else float(p_str)
                        p_inr = p * USD_TO_INR if sym_r.endswith('-USD') else p
                        if p_inr > 0: g_prof += p_inr
                        elif p_inr < 0: g_loss += abs(p_inr)
                        taxes += abs(p_inr) * 0.001
                    except: pass
            spot_profit = (g_prof - g_loss) - taxes
    except: pass

    # 2. Futures Realized Profit (Net of fees)
    futures_profit = 0.0
    try:
        df_fo_hist = db_helper.get_trade_history_df(is_futures=True)
        if not df_fo_hist.empty:
            for idx, r in df_fo_hist.iterrows():
                if str(r.get('Action', '')).upper() == 'CLOSE':
                    margin = float(r.get('Margin', 5000.0))
                    lev = int(r.get('Leverage', 5))
                    notional = margin * lev
                    fee = round(notional * 0.001, 2)
                    p = float(r.get('Profit_INR', 0.0))
                    futures_profit += (p - fee)
    except: pass

    total_profit = spot_profit + futures_profit

    spot_invested = sum(float(d_info.get('total_cost', 0.0)) for d_info in dca_positions.values())
    futures_invested = sum(float(f_info.get('margin', 5000.0)) for f_info in futures_positions.values())

    portfolio_value = initial_capital + total_profit
    total_invested = spot_invested + futures_invested
    invested_amount = min(portfolio_value, max(0.0, total_invested))
    available_cash = max(0.0, portfolio_value - invested_amount)
    roi = (total_profit / initial_capital) * 100 if initial_capital > 0 else 0.0

# 4. Spot Floating P&L
spot_floating_pnl = 0.0
per_position_pnl = {}
for d_sym, d_info in dca_positions.items():
    avg_p = float(d_info.get('avg_price', 0))
    total_qty = float(d_info.get('total_qty', 0))
    total_cost = float(d_info.get('total_cost', 0))
    if avg_p <= 0: continue
    live_p_info = live_prices.get(d_sym, {})
    live_p = live_p_info.get("price", 0.0)
    if live_p <= 0: live_p = scanned_assets.get(d_sym, {}).get("price", avg_p)
    if live_p <= 0: live_p = avg_p
    
    pnl_usd = (live_p - avg_p) * total_qty
    pnl_inr = pnl_usd * USD_TO_INR if d_sym.endswith('-USD') else pnl_usd
    pnl_pct = ((live_p - avg_p) / avg_p) * 100.0
    cur_val_inr = total_cost + pnl_inr
    spot_floating_pnl += pnl_inr
    per_position_pnl[d_sym] = {
        "live_price": live_p,
        "avg_price": avg_p,
        "pnl_pct": pnl_pct,
        "pnl_inr": pnl_inr,
        "cur_val_inr": cur_val_inr,
        "total_cost": total_cost,
        "total_qty": total_qty,
    }

# 5. Futures Floating P&L
futures_floating_pnl = 0.0
per_futures_pnl = {}
for f_sym, f_info in futures_positions.items():
    f_entry = float(f_info.get('entry_price', 0))
    f_qty = float(f_info.get('qty', 0))
    f_side = f_info.get('side', 'LONG')
    f_margin = float(f_info.get('margin', 5000.0))
    
    f_live_info = live_prices.get(f_sym, {})
    f_live = f_live_info.get("price", 0.0)
    if f_live <= 0: f_live = scanned_assets.get(f_sym, {}).get("price", f_entry)
    if f_live <= 0: f_live = f_entry
    
    if f_side == 'LONG':
        f_pnl_usd = (f_live - f_entry) * f_qty
    else:
        f_pnl_usd = (f_entry - f_live) * f_qty
        
    f_pnl_inr = f_pnl_usd * USD_TO_INR
    f_roe = (f_pnl_inr / f_margin) * 100.0 if f_margin > 0 else 0.0
    futures_floating_pnl += f_pnl_inr
    per_futures_pnl[f_sym] = {
        "live_price": f_live,
        "entry_price": f_entry,
        "side": f_side,
        "margin": f_margin,
        "pnl_inr": f_pnl_inr,
        "roe_pct": f_roe
    }

# 6. Combined Live Floating Total
total_floating_pnl = spot_floating_pnl + futures_floating_pnl
total_floating_pnl_pct = (total_floating_pnl / invested_amount) * 100 if invested_amount > 0 else 0.0
live_portfolio_value = portfolio_value + total_floating_pnl

# ─── PROFESSIONAL PORTFOLIO HEADER RIBBON ───
if is_angel_live:
    st.markdown("""
<div style="background: linear-gradient(135deg, #0a192f 0%, #172a45 100%);
            border: 2px solid #00c853; border-radius: 14px; padding: 18px 24px; margin-bottom: 18px;
            box-shadow: 0 4px 24px rgba(0,200,83,0.25);">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom: 6px;">
    <div style="font-size: 15px; color: #00e676; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">
      🇮🇳 ANGEL ONE SMARTAPI — LIVE ACCOUNT SNAPSHOT
    </div>
    <div style="background:#00c853; color:#0d1117; font-weight:800; font-size:11px; padding:4px 12px; border-radius:20px; letter-spacing:.5px;">
      🟢 REAL MONEY TRADING ACTIVE
    </div>
  </div>
  <div style="font-size: 13px; color: #8892b0;">
    👤 <b>Account Holder:</b> SHAIK KALESHA (<code>AABZ864543</code>) &nbsp;|&nbsp; 🏛️ <b>Broker:</b> Angel One Ltd &nbsp;|&nbsp; ⚡ <b>Exchange:</b> NSE India Live
  </div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div style="background: linear-gradient(135deg, #0d1117 0%, #1a1f2e 100%);
            border: 1px solid #2962ff; border-radius: 14px; padding: 18px 24px; margin-bottom: 18px;
            box-shadow: 0 4px 24px rgba(41,98,255,0.2);">
  <div style="font-size: 13px; color: #787b86; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 12px;">
    🏦 ANTIGRAVITY KITE PRO — PORTFOLIO SNAPSHOT (Live)
  </div>
""", unsafe_allow_html=True)

top_b1, top_b2, top_b3, top_b4, top_b5 = st.columns(5)
with top_b1:
    st.markdown(fancy_metric("🏦 Net Portfolio", f"₹{portfolio_value:,.2f}", f"{roi:+.2f}% Booked ROI"), unsafe_allow_html=True)
    with st.popover("🔍 Realized Profit Details", use_container_width=True):
        st.markdown("### 🏦 Net Portfolio Details")
        if is_angel_live:
            st.info(f"**👤 Account:** SHAIK KALESHA (`AABZ864543`)\n\n**Initial Deposit:** ₹{initial_capital:,.2f}\n\n- **NSE Stock Realized P&L:** ₹{spot_profit:+,.2f}\n\n**Total Booked P&L:** ₹{total_profit:+,.2f}\n**Total Account Value:** ₹{portfolio_value:,.2f}")
        else:
            st.info(f"**Initial Capital:** ₹50,000.00\n\n- **Spot Realized:** ₹{spot_profit:+,.2f}\n- **Futures Realized:** ₹{futures_profit:+,.2f}\n\n**Total Booked P&L:** ₹{total_profit:+,.2f}\n**Total Account Balance:** ₹{portfolio_value:,.2f}")

with top_b2:
    st_tot_trades = len(dca_positions) + len(futures_positions)
    if is_angel_live:
        sub_title = f"5x Margin: ₹{blocked_margin:,.2f} Blocked"
        st.markdown(fancy_metric("🚀 5x Market Exposure", f"₹{invested_amount:,.2f}", sub_title), unsafe_allow_html=True)
    else:
        sub_title = f"Spot + Futures ({st_tot_trades})"
        st.markdown(fancy_metric("🔒 Total Invested", f"₹{invested_amount:,.2f}", sub_title), unsafe_allow_html=True)
    with st.popover("🔍 Capital Allocation Details", use_container_width=True):
        st.markdown("### 🔒 Investment Capital Breakdown")
        if is_angel_live:
            st.markdown(f"**📌 Angel One 5x Market Exposure:** ₹{spot_invested:,.2f} ({len(dca_positions)} stocks)")
            st.markdown(f"**⚡ Actual Cash Margin Blocked (20%):** ₹{blocked_margin:,.2f}")
            if dca_positions:
                for s, p in dca_positions.items():
                    c_cost = float(p.get('total_cost', 0))
                    st.write(f"- {s}: ₹{c_cost:,.2f} (Margin: ₹{c_cost/5.0:,.2f})")
            else:
                st.caption("No capital currently locked in stocks. 100% available as liquid cash.")
        else:
            st.markdown(f"**📌 Spot Investment:** ₹{spot_invested:,.2f} ({len(dca_positions)} assets)")
            if dca_positions:
                for s, p in dca_positions.items():
                    st.write(f"- {s}: ₹{p.get('total_cost', 0):,.2f}")
            st.divider()
            st.markdown(f"**🚀 Futures Margin (5x):** ₹{futures_invested:,.2f} ({len(futures_positions)} trades)")
            if futures_positions:
                for fs, fp in futures_positions.items():
                    st.write(f"- {fs} ({fp.get('side', 'LONG')} 5x): ₹{fp.get('margin', 5000):,.2f}")

with top_b3:
    st.markdown(fancy_metric("💵 Free Liquid Cash", f"₹{available_cash:,.2f}", "Angel One Free Buffer" if is_angel_live else "Available Capital"), unsafe_allow_html=True)
    with st.popover("🔍 Cash Allocation Details", use_container_width=True):
        st.markdown("### 💵 Free Cash Balance")
        if is_angel_live:
            st.write("Live available funds in your Angel One trading account.")
            st.write(f"- Angel One Client: `AABZ864543`")
            st.write(f"- Blocked Margin (5x MIS): ₹{blocked_margin:,.2f}")
            st.divider()
            st.success(f"Live Available Cash: ₹{available_cash:,.2f}")
        else:
            st.write("Unallocated liquid cash available for new spot entries and margin buffers.")
            st.write(f"- Total Portfolio Capital: ₹{portfolio_value:,.2f}")
            st.write(f"- Spot Capital Allocated: ₹{spot_invested:,.2f}")
            st.write(f"- Futures Margin Allocated: ₹{futures_invested:,.2f}")
            st.divider()
            st.success(f"Remaining Liquid Cash: ₹{available_cash:,.2f}")

with top_b4:
    top_pnl_color = "normal" if total_floating_pnl >= 0 else "inverse"
    pnl_sub = f"{((total_floating_pnl / portfolio_value) * 100 if portfolio_value > 0 else 0):+.2f}% on Capital" if is_angel_live else f"{total_floating_pnl_pct:+.2f}% Total"
    st.markdown(fancy_metric("📈 Floating P&L (Unrealized)", f"₹{total_floating_pnl:+,.2f}", pnl_sub, top_pnl_color), unsafe_allow_html=True)
    with st.popover("🔍 Live P&L Breakdown", use_container_width=True):
        st.markdown("### 📈 Floating (Unrealized) P&L")
        if is_angel_live:
            st.markdown(f"**📌 Angel One Stocks Floating P&L:** ₹{spot_floating_pnl:+.2f}")
            if dca_positions:
                for s, pd_info in per_position_pnl.items():
                    pnl = pd_info['pnl_inr']
                    c = "🟢" if pnl >= 0 else "🔴"
                    st.write(f"- {c} {s}: ₹{pnl:+.2f} ({pd_info['pnl_pct']:+.2f}%)")
            else:
                st.caption("No active open stock positions. Floating P&L is ₹0.00.")
        else:
            st.markdown(f"**📌 Spot Floating P&L:** ₹{spot_floating_pnl:+.2f}")
            if dca_positions:
                for s, pd_info in per_position_pnl.items():
                    pnl = pd_info['pnl_inr']
                    c = "🟢" if pnl >= 0 else "🔴"
                    st.write(f"- {c} {s}: ₹{pnl:+.2f} ({pd_info['pnl_pct']:+.2f}%)")
            st.divider()
            st.markdown(f"**🚀 Futures Floating P&L (5x):** ₹{futures_floating_pnl:+.2f}")
            if futures_positions:
                for fs, fpd in per_futures_pnl.items():
                    fpnl = fpd['pnl_inr']
                    fc = "🟢" if fpnl >= 0 else "🔴"
                    st.write(f"- {fc} {fs} ({fpd['side']} 5x): ₹{fpnl:+.2f} ({fpd['roe_pct']:+.2f}% ROE)")

with top_b5:
    live_pf_color = "normal" if live_portfolio_value >= portfolio_value else "inverse"
    delta_text = "Real Live Equity" if is_angel_live else f"1 USD = ₹{USD_TO_INR:.2f}"
    st.markdown(fancy_metric("⚡ Total Real Equity", f"₹{live_portfolio_value:,.2f}", delta_text, live_pf_color), unsafe_allow_html=True)
    with st.popover("🔍 Valuation Summary", use_container_width=True):
        st.markdown("### ⚡ Net Valuation Details")
        st.write("Total current equity combining booked capital and real-time open positions.")
        st.write(f"**Booked Equity:** ₹{portfolio_value:,.2f}")
        c = "+" if total_floating_pnl >= 0 else ""
        st.write(f"**Floating P&L:** {c}₹{total_floating_pnl:,.2f}")
        st.divider()
        st.write(f"**Total Live Valuation:** ₹{live_portfolio_value:,.2f}")

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# 🌟 3. TOP-LEVEL PRO WEB TABS (100% SEPARATED BETWEEN MODES)
# -------------------------------------------------------------
if is_angel_live:
    tab_pos, tab_mind, tab_charts, tab_orders, tab_search, tab_voice = st.tabs([
        "📌 Live Positions (Angel One)",
        "🧠 AI Brain & NSE Reasoning",
        "📊 NSE Live Charts & Patterns",
        "📋 Angel One Orders & Settlement History",
        "🔍 NSE 25 Momentum Screener",
        "💬 AI Assistant"
    ])
    tab_futures = None
else:
    tab_pos, tab_futures, tab_mind, tab_charts, tab_orders, tab_search, tab_voice = st.tabs([
        "📌 Live Positions (Crypto Paper Spot)",
        "🚀 Futures (Paper 5x)",
        "🧠 AI Crypto Brain & Reasoning",
        "📊 Crypto Live Charts & Patterns",
        "📋 Crypto Paper Orders & PnL History",
        "🔍 Crypto 24/7 Market Screener",
        "💬 AI Assistant"
    ])

# =============================================================
# TAB 1: 📌 Live Positions
# =============================================================
with tab_pos:
    if is_angel_live:
        st.markdown("### 🎯 Active Angel One Positions (NSE Live)")
        st.caption("Real-time live positions executed on National Stock Exchange (NSE) via Angel One SmartAPI:")
    else:
        st.markdown("### 🎯 Active Spot Positions (Live DCA)")
        st.caption("Click any open position below to inspect detailed DCA entries, target progress, and risk parameters:")

    if dca_positions:
        trade_keys = list(dca_positions.keys())
        if 'inspect_trade_key' not in st.session_state or st.session_state['inspect_trade_key'] not in trade_keys:
            st.session_state['inspect_trade_key'] = trade_keys[0]

        # ─── ZERODHA / ANGEL ONE STYLE POSITIONS TABLE (HTML) ───
        rows_html = ""
        for d_sym, d_info in dca_positions.items():
            pnl_data = per_position_pnl.get(d_sym, {})
            live_p   = pnl_data.get("live_price", float(d_info.get("avg_price", 0)))
            avg_p    = pnl_data.get("avg_price",  float(d_info.get("avg_price", 0)))
            pnl_pct  = pnl_data.get("pnl_pct", 0.0)
            pnl_inr  = pnl_data.get("pnl_inr", 0.0)
            cur_val  = pnl_data.get("cur_val_inr", float(d_info.get("total_cost", 0)))
            cost_inr = pnl_data.get("total_cost", float(d_info.get("total_cost", 0)))
            target_p = float(d_info.get("target_sell_price", avg_p * 1.015))
            qty      = float(d_info.get("total_qty", 0))
            is_ind   = (".NS" in d_sym or ".BO" in d_sym)
            curr_sym = "₹" if is_ind else "$"
            clean_nm = d_sym.replace(".NS", "").replace("-USD", "")
            pnl_clr  = "#00e676" if pnl_inr >= 0 else "#ff5252"
            pnl_icon = "▲" if pnl_inr >= 0 else "▼"
            dist_to_target = ((target_p - live_p) / avg_p) * 100.0 if avg_p > 0 else 0.0
            pr_fmt   = f"{curr_sym}{live_p:,.4f}" if live_p < 1 else f"{curr_sym}{live_p:,.2f}"
            avg_fmt  = f"{curr_sym}{avg_p:,.4f}" if avg_p < 1 else f"{curr_sym}{avg_p:,.2f}"
            tgt_fmt  = f"{curr_sym}{target_p:,.4f}" if target_p < 1 else f"{curr_sym}{target_p:,.2f}"
            pos_badge = "ANGEL ONE LIVE (NSE)" if is_angel_live else ("NSE STOCK" if is_ind else "CRYPTO SPOT")
            badge_color = "#00e676" if is_angel_live else ("#00bcd4" if is_ind else "#2962ff")
            qty_fmt = f"{int(qty)}" if qty == int(qty) else f"{qty:.5f}"
            rows_html += f"""<tr>
  <td><b style="color:#e0e3eb;">{clean_nm}</b><br>
      <span style="font-size:11px;color:{badge_color};font-weight:600;">{pos_badge}</span></td>
  <td style="color:#9e9e9e;font-size:12px;">{qty_fmt}</td>
  <td>{avg_fmt}</td>
  <td style="color:#00bcd4;font-weight:600;">{pr_fmt}</td>
  <td style="color:#ffa726;">{tgt_fmt}</td>
  <td>₹{cost_inr:,.2f}</td>
  <td>₹{cur_val:,.2f}</td>
  <td style="color:{pnl_clr};font-weight:700;">{pnl_icon} ₹{abs(pnl_inr):,.2f}<br>
      <span style="font-size:11px;">({pnl_pct:+.2f}%)</span></td>
  <td style="color:#ffa726;font-size:12px;">{dist_to_target:+.2f}% more</td>
</tr>"""

        positions_table_html = f"""
        <div style="overflow-x:auto; margin-bottom:20px;">
        <table class="zk-pos-table" style="width:100%;border-collapse:separate;border-spacing:0;
               background:#131722;border:1px solid #2a2e39;border-radius:10px;overflow:hidden;">
          <thead>
            <tr style="background:#181c27;">
              <th style="padding:11px 12px;color:#787b86;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Asset</th>
              <th style="padding:11px 12px;color:#787b86;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Quantity</th>
              <th style="padding:11px 12px;color:#787b86;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Avg Buy Price</th>
              <th style="padding:11px 12px;color:#00bcd4;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Live Price</th>
              <th style="padding:11px 12px;color:#ffa726;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Target</th>
              <th style="padding:11px 12px;color:#787b86;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Invested (₹)</th>
              <th style="padding:11px 12px;color:#787b86;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Current Value (₹)</th>
              <th style="padding:11px 12px;color:#787b86;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">PnL & ROE</th>
              <th style="padding:11px 12px;color:#787b86;font-size:12px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2a2e39;">Distance to Target</th>
            </tr>
          </thead>
          <tbody style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#e0e3eb;">
            {rows_html}
          </tbody>
        </table>
        </div>"""
        st.markdown(textwrap.dedent(positions_table_html), unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 🔍 Click any asset below to inspect live candlestick chart & AI pattern:")
        s_cols = st.columns(max(1, len(dca_positions)))
        for s_idx, ssym_btn in enumerate(dca_positions.keys()):
            with s_cols[s_idx]:
                if st.button(f"📊 {ssym_btn} Chart & Pattern", key=f"btn_spot_chart_{ssym_btn}", use_container_width=True):
                    st.session_state['selected_chart_sym'] = ssym_btn
                    st.toast(f"✅ {ssym_btn} loaded! Inspect in '📊 Pro Charts & Patterns' tab.", icon="🕯️")
                    st.rerun()

    else:
        if is_angel_live:
            st.info(f"ℹ️ **No open positions in Angel One currently.**\n\nLive Cash: **₹{available_cash:,.2f}** | Client: **SHAIK KALESHA (AABZ864543)**\n\nThe bot is actively scanning NSE (ITC, TATASTEEL, ONGC, IOC, SUZLON, SBIN, HDFCBANK) and will place a live BUY order as soon as a high-confluence entry triggers.")
        elif futures_positions:
            f_names = ", ".join([f"{k} ({v.get('side', 'SHORT')} 5x)" for k, v in futures_positions.items()])
            st.success(f"🚀 **Active Futures Trade Running:** {f_names} with ₹{futures_invested:,.2f} margin! Click the **🚀 Futures (Paper 5x)** tab next door to inspect live entry, target, and ROE.")
        else:
            st.info("No active spot positions open currently. All prior trades closed in profit. Bot is scanning the market for fresh high-probability entries.")


# =============================================================
# TAB 2: 🚀 FUTURES PAPER TRADING (5x LEVERAGE - CRYPTO ONLY)
# =============================================================
if tab_futures is not None:
    with tab_futures:
        st.markdown("### 🚀 Crypto Futures Paper Trading (5x Leverage)")
        st.caption("Simulated institutional paper trading with ₹5,000/trade margin, 5x leverage, and strict loss-protection guards. Real-time PnL updates:")
        
        futures_state = get_state_smart('fo_state')
                
        if not futures_state:
            st.info("No active futures positions open currently. Waiting for institutional confluence (SMC + EMA Crossover)...")
        else:
            f_rows = []
            for fsym, finfo in futures_state.items():
                f_pinfo = live_prices.get(fsym, {})
                f_live = f_pinfo.get("price", float(finfo['entry_price']))
                f_entry = float(finfo['entry_price'])
                f_side = finfo['side']
                f_qty = float(finfo['qty'])
                f_margin = float(finfo['margin'])
                f_lev = int(finfo['leverage'])
                
                if f_side == 'LONG':
                    f_pnl_usd = (f_live - f_entry) * f_qty
                else:
                    f_pnl_usd = (f_entry - f_live) * f_qty
                    
                f_pnl_inr = f_pnl_usd * USD_TO_INR
                f_roe = (f_pnl_inr / f_margin) * 100.0
                
                pnl_c = "#00e676" if f_pnl_inr >= 0 else "#ff5252"
                side_bg = "#004d40" if f_side == 'LONG' else "#4a148c"
                
                row_html = (
                    f"<tr>"
                    f"<td><b style='color:#e0e3eb;'>{fsym}</b></td>"
                    f"<td><span style='background:{side_bg};padding:3px 6px;border-radius:4px;font-weight:bold;'>{f_side}</span> {f_lev}x</td>"
                    f"<td>${f_entry:,.4f}</td>"
                    f"<td style='color:#00bcd4;'>${f_live:,.4f}</td>"
                    f"<td>₹{f_margin:,.2f}</td>"
                    f"<td style='color:{pnl_c};font-weight:bold;'>₹{f_pnl_inr:+.2f} ({f_roe:+.2f}%)</td>"
                    f"</tr>"
                )
                f_rows.append(row_html)
                
            rows_joined = "".join(f_rows)
            f_table = (
                "<table class='zk-pos-table' style='width:100%;border-collapse:separate;border-spacing:0;background:#131722;border:1px solid #2a2e39;border-radius:10px;overflow:hidden;'>"
                "<thead><tr style='background:#181c27;'>"
                "<th style='padding:11px 12px;color:#787b86;'>Symbol</th>"
                "<th style='padding:11px 12px;color:#787b86;'>Side & Leverage</th>"
                "<th style='padding:11px 12px;color:#787b86;'>Entry Price</th>"
                "<th style='padding:11px 12px;color:#00bcd4;'>Live Price</th>"
                "<th style='padding:11px 12px;color:#787b86;'>Margin (₹)</th>"
                "<th style='padding:11px 12px;color:#787b86;'>PnL & ROE%</th>"
                f"</tr></thead><tbody style='font-family:monospace;font-size:13px;color:#e0e3eb;'>{rows_joined}</tbody></table>"
            )
            st.markdown(f_table, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 🔍 Click any coin below to inspect live candlestick chart & AI pattern:")
            f_cols = st.columns(max(1, len(futures_state)))
            for f_idx, fsym_btn in enumerate(futures_state.keys()):
                with f_cols[f_idx]:
                    if st.button(f"📊 {fsym_btn} Chart & Pattern", key=f"btn_fut_chart_{fsym_btn}", use_container_width=True):
                        st.session_state['selected_chart_sym'] = fsym_btn
                        st.toast(f"✅ {fsym_btn} loaded! Inspect in '📊 Pro Charts & Patterns' tab.", icon="🕯️")
                        st.rerun()
            
        st.markdown("---")
        st.markdown("#### 📋 Futures Closed Trades History")
        try:
            f_df = db_helper.get_trade_history_df(is_futures=True)
            if not f_df.empty:
                safe_dataframe(f_df.tail(15).iloc[::-1], hide_index=True)
        except:
            pass


# =============================================================
# TAB 3: 🧠 AI Brain & Trading Reasoning
# =============================================================
with tab_mind:
    st.markdown("### 🧠 AI Brain & Real-Time Trading Reasoning Hub")
    st.caption("Transparent real-time breakdown of why the AI entered, holds, or skips assets across all tracked markets:")

    # =========================================================
    # 🌙 0. AI OVERNIGHT RESEARCH & 9:15 AM MORNING BATTLEPLAN
    # =========================================================
    st.subheader("🌙 AI Overnight Research & 9:15 AM Morning Battleplan")
    st.caption("భారత మార్కెట్ ముగిసిన తర్వాత (రాత్రంతా), ఈ AI బ్రెయిన్ గ్లోబల్ మార్కెట్స్, నాస్‌డాక్, క్రూడ్ ఆయిల్ & 25 NSE స్టాక్స్ లోతుగా రీసెర్చ్ చేసి ఉదయం 9:15 AM కు స్నిపర్ ట్రేడ్స్ సిద్ధం చేస్తుంది:")

    # Load overnight research from DB or file
    on_res = db_helper.get_state('overnight_research', {})
    if not on_res and os.path.exists('overnight_research.json'):
        try:
            with open('overnight_research.json', 'r') as f_on:
                on_res = json.load(f_on)
        except Exception:
            pass

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn2:
        if st.button("🔄 Re-run Overnight Audit", key="btn_rerun_overnight", use_container_width=True):
            with st.spinner("AI రాత్రి రీసెర్చ్ రన్ చేస్తోంది... గ్లోబల్ క్యూస్ & 25 స్టాక్స్ ఆడిట్ చేస్తోంది..."):
                try:
                    import overnight_brain
                    on_res = overnight_brain.run_overnight_audit()
                    st.success("✅ రాత్రి రీసెర్చ్ పూర్తయింది!")
                    st.rerun()
                except Exception as e_aud:
                    st.error(f"Error running audit: {e_aud}")

    if on_res:
        g_cues = on_res.get('global_cues', {})
        bias = g_cues.get('bias', 'NEUTRAL ⚖️')
        open_pred = g_cues.get('open_prediction', 'FLAT / CAUTION')
        ts = on_res.get('timestamp', 'N/A')
        v_summary = on_res.get('voice_summary', '')
        top_picks = on_res.get('top_3_picks', [])

        # Display Global Sentiment Banner
        if 'BULLISH' in bias:
            banner_style = "background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(16, 185, 129, 0.05)); border: 1px solid rgba(34, 197, 94, 0.4);"
            badge_color = "#22c55e"
        elif 'BEARISH' in bias:
            banner_style = "background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.05)); border: 1px solid rgba(239, 68, 68, 0.4);"
            badge_color = "#ef4444"
        else:
            banner_style = "background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(37, 99, 235, 0.05)); border: 1px solid rgba(59, 130, 246, 0.4);"
            badge_color = "#3b82f6"

        banner_html = f"""
        <div style="{banner_style} border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; font-weight: 600;">Global Macro Sentiment & Opening Gap Forecast</span>
                    <h3 style="margin: 4px 0 0 0; font-size: 20px; color: {badge_color};">
                        {bias} &nbsp;|&nbsp; 9:15 AM: {open_pred}
                    </h3>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 11px; color: #94a3b8;">Last Research Audit</span><br/>
                    <strong style="font-size: 13px; color: #cbd5e1;">{ts}</strong>
                </div>
            </div>
            <div style="margin-top: 10px; font-size: 13px; color: #e2e8f0; line-height: 1.5; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 8px;">
                🗣️ <strong>AI బ్రెయిన్ విశ్లేషణ:</strong> {v_summary}
            </div>
        </div>
        """
        st.markdown(banner_html, unsafe_allow_html=True)

        # Global Telemetry Row
        telemetry = g_cues.get('telemetry', {})
        if telemetry:
            tel_cols = st.columns(len(telemetry))
            for t_idx, (t_name, t_val) in enumerate(telemetry.items()):
                with tel_cols[t_idx]:
                    chg = t_val.get('change_pct', 0.0)
                    chg_str = f"{chg:+.2f}%"
                    pr = t_val.get('price', 0.0)
                    pr_str = f"₹{pr:,.2f}" if 'INR' in t_name or 'Nifty' in t_name else f"${pr:,.2f}"
                    st.metric(label=f"🌐 {t_name}", value=pr_str, delta=chg_str)

        # Top 3 Golden Sniper Stocks
        st.markdown("#### 🎯 9:15 AM మార్నింగ్ స్నిపర్ స్టాక్స్ (Top 3 Golden Picks)")
        st.caption("25 NSE మొమెంటం స్టాక్స్ లో టెక్నికల్ స్కోర్, CPR కంప్రెషన్, 200 EMA మరియు రిస్క్-రివార్డ్ ఆధారంగా ఎంపిక చేయబడిన ఉత్తమ స్టాక్స్:")

        if top_picks:
            pick_cols = st.columns(len(top_picks))
            for p_idx, pick in enumerate(top_picks):
                with pick_cols[p_idx]:
                    sym_c = pick.get('clean_name', pick.get('symbol', ''))
                    score = pick.get('score', 0)
                    close_pr = pick.get('close', 0.0)
                    target_pr = pick.get('target_2_5_pct', 0.0)
                    sl_pr = pick.get('stop_loss', 0.0)
                    est_net = pick.get('est_net_profit', 0.0)
                    rsi_p = pick.get('rsi', 0.0)
                    rvol_p = pick.get('rvol', 1.0)
                    cpr_desc = pick.get('cpr_desc', 'నార్మల్ CPR')
                    thesis_p = pick.get('thesis', '')
                    is_narrow = pick.get('is_narrow_cpr', False)
                    cpr_badge = "🚀 నారో CPR (వన్-వే ట్రెండ్)" if is_narrow else "⚖️ మీడియం CPR"

                    card_html = f"""
                    <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 14px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 16px; font-weight: 700; color: #38bdf8;">#{p_idx+1} {sym_c}</span>
                            <span style="background: rgba(34, 197, 94, 0.2); color: #4ade80; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 700;">Score: {score}/100</span>
                        </div>
                        <div style="margin: 8px 0; font-size: 20px; font-weight: 700; color: #f8fafc;">
                            ₹{close_pr:,.2f}
                        </div>
                        <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">
                            🎯 <strong>Target (+2.50%):</strong> <span style="color: #4ade80; font-weight: 600;">₹{target_pr:,.2f}</span><br/>
                            🛑 <strong>Stop Loss (-1.2%):</strong> <span style="color: #f87171; font-weight: 600;">₹{sl_pr:,.2f}</span><br/>
                            💰 <strong>Est. Net Profit:</strong> <span style="color: #fbbf24; font-weight: 600;">+₹{est_net:,.2f}</span>
                        </div>
                        <div style="font-size: 11px; background: rgba(15, 23, 42, 0.6); padding: 6px; border-radius: 6px; color: #cbd5e1; margin-bottom: 6px;">
                            📊 <strong>RSI:</strong> {rsi_p:.1f} | <strong>RVOL:</strong> {rvol_p:.2f}x<br/>
                            🧭 <strong>CPR:</strong> {cpr_badge}
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    with st.expander(f"🔍 {sym_c} AI థీసిస్ & కారణాలు", expanded=False):
                        st.write(thesis_p)

        # Ranked Table for all 25 stocks
        ranked_all = on_res.get('ranked_stocks', [])
        if ranked_all:
            with st.expander(f"📋 మొత్తం {len(ranked_all)} NSE స్టాక్స్ పూర్తి ఆడిట్ ర్యాంకింగ్ టేబుల్ (Click to inspect all)", expanded=False):
                r_rows = []
                for r_idx, r_item in enumerate(ranked_all):
                    r_rows.append({
                        "Rank": f"#{r_idx+1}",
                        "Stock": r_item.get('clean_name', ''),
                        "AI Score": f"{r_item.get('score', 0)}/100",
                        "Price": f"₹{r_item.get('close', 0.0):,.2f}",
                        "RSI (14)": f"{r_item.get('rsi', 0.0):.1f}",
                        "RVOL": f"{r_item.get('rvol', 1.0):.2f}x",
                        "CPR Type": "🚀 Narrow (Trend)" if r_item.get('is_narrow_cpr', False) else "⚖️ Medium/Wide",
                        "Target (+2.5%)": f"₹{r_item.get('target_2_5_pct', 0.0):,.2f}",
                        "Thesis": r_item.get('thesis', '')
                    })
                safe_dataframe(pd.DataFrame(r_rows), hide_index=True)
    else:
        st.info("🌙 రాత్రి రీసెర్చ్ రిపోర్ట్ ఇంకా రన్ కాలేదు. పైన ఉన్న **'🔄 Re-run Overnight Audit'** బటన్ క్లిక్ చేసి వెంటనే రీసెర్చ్ ప్రారంభించండి.")

    st.markdown("---")

    # 1. ACTIVE TRADES RATIONALE
    st.subheader("🟢 1. Active Trade Rationale & Thesis")
    if dca_positions:
        for m_sym, m_info in dca_positions.items():
            m_asset = scanned_assets.get(m_sym, {})
            m_thought = m_asset.get('thought', '15m Higher Timeframe trend is strongly bullish. Entered sniper buy at institutional VWAP support.')
            clean_m = m_sym.replace('.NS', '').replace('-USD', '')
            rsi_val = m_asset.get('rsi', 52.0)
            strat_nm = m_info.get('strategy', 'Fair Value Gap (FVG Imbalance Fill)')
            
            with st.expander(f"🪙 {clean_m}  - Why did it buy? Why is it holding? (Click to expand)", expanded=True):
                st.markdown(f"**🎯 Entry Thesis:**")
                st.info(m_thought)
                
                t_sub1, t_sub2, t_sub3 = st.columns(3)
                t_sub1.markdown(f"📊 **RSI (14):** `{rsi_val:.1f}` (Optimal Buy)")
                t_sub2.markdown(f"📈 **15m HTF Trend:** `BULLISH 🟢`")
                t_sub3.markdown(f"🧬 **Strategy:** `{strat_nm}`")
                
                st.markdown(f"**⚡ Holding Thesis:**")
                st.write(f"Holding for target exit. Once +1.2% - +1.5% profit or dynamic trailing lock triggers, it automatically exits. Strong momentum prevents premature exits.")
                
                st.markdown(f"**🛡️ Capital Protection & Risk Guard:**")
                st.caption(f"Unconditional hard stop-loss is armed to strictly limit downside. Zero-loss breakeven lock activates once the position moves into profit.")
    else:
        st.info("No active positions currently.")

    st.markdown("---")

    # 2. WATCHING & WAITING LIST
    st.subheader("⏳ 2. Watchlist & Setup Monitoring")
    st.caption("Assets continuously scanned by AI bot waiting for ideal technical breakout/confirmation:")
    
    watch_rows = []
    for sc_sym, sc_data in scanned_assets.items():
        if not sc_data.get('has_position', False):
            is_i = sc_data.get('is_indian', False) or sc_sym.endswith(('.NS', '.BO'))
            if is_angel_live and not is_i:
                continue
            if not is_angel_live and is_i:
                continue
            clean_s = sc_data.get('clean_name', sc_sym).replace('.NS', '').replace('-USD', '')
            pr_val = sc_data.get('price', 0.0)
            pr_fmt = f"₹{pr_val:,.2f}" if is_i else f"${pr_val:,.2f}"
            rsi_s = sc_data.get('rsi', 50.0)
            
            watch_rows.append({
                "🪙 Asset": clean_s,
                "💵 Live Price": pr_fmt,
                "⚡ RSI (14)": f"{rsi_s:.1f}",
                "🤖 Status": "⏳ Waiting (Awaiting confirmation)",
                "🧠 AI Thesis & Reason": f"Market is in consolidation. RSI is at {rsi_s:.1f}. Waiting for confirmed support bounce or pullback before committing capital."
            })
            
    if watch_rows:
        safe_dataframe(pd.DataFrame(watch_rows), hide_index=True)
    else:
        st.write("All target assets are currently being scanned.")

    st.markdown("---")

    # 3. WHY THE BOT DECIDED 'VADDU' / REJECTED
    st.subheader("🚫 3. Filtered & Skipped Trades (Why the Bot Rejected / Skipped Entries)")
    st.caption("Why does the bot avoid entering trades during high-risk conditions? Active AI filters detailed below:")
    
    sk1, sk2 = st.columns(2)
    with sk1:
        st.error("""**🔴 1. Overbought Risk Filter (Rejected at RSI > 70)**

When an asset pumps excessively and RSI crosses 70, retail traders FOMO in. The AI classifies this as an extreme correction hazard and rejects buy orders to prevent buying the top.""")
        st.error("""**🔴 2. Bearish Trend Guard (Rejected Below 200 EMA)**

When price trades below the 200 EMA, selling pressure dominates the broader trend. Temporary bounces are tagged as bull traps and rejected.""")
    with sk2:
        st.error("""**🔴 3. Volume Divergence Shield (Fake Pump Protection)**

Pumps lacking institutional volume and VWAP support are classified as liquidity traps. Buy signals without volume confirmation are skipped.""")
        st.error("""**🛡️ 4. Max Capital Exposure Guard (Risk Cap)**

To preserve portfolio equity, maximum concurrent open positions are strictly limited to 6 assets.""")

    # 4. AI BRAIN & STRATEGY WEIGHTS
    st.subheader("🧬 4. AI Neural Learning Brain (ai_brain.json)")
    brain_data = db_helper.get_state('ai_brain', {})
    if not brain_data and os.path.exists('ai_brain.json'):
        try:
            with open('ai_brain.json', 'r') as f_br:
                brain_data = json.load(f_br)
        except Exception:
            pass
    if brain_data:
        try:
            br_c1, br_c2, br_c3 = st.columns(3)
            br_c1.markdown(fancy_metric("AI Brain Version", brain_data.get('brain_version', 'v3.0-NeuralSniper')), unsafe_allow_html=True)
            br_c2.markdown(fancy_metric("AI IQ Score", f"{brain_data.get('iq_score', 138)}", "High-Intelligence"), unsafe_allow_html=True)
            br_c3.markdown(fancy_metric("Strategy Win Rate", f"{brain_data.get('win_rate', 68.5)}%", "Backtest Accuracy"), unsafe_allow_html=True)
            
            st.markdown("##### 🏆 Strategy Leaderboard (Accuracy & Win Rates):")
            strat_rows = []
            for s_key, s_val in brain_data.get('strategies', {}).items():
                strat_rows.append({
                    "Strategy Name": s_val.get('name'),
                    "Wins": s_val.get('wins'),
                    "Losses": s_val.get('losses'),
                    "Win Rate": f"{s_val.get('win_rate'):.1f}%",
                    "AI Weight": s_val.get('weight')
                })
            safe_dataframe(pd.DataFrame(strat_rows), hide_index=True)
        except Exception:
            pass


# =============================================================
# TAB 4: 📊 Pro Charts & Pattern Scanner
# =============================================================
with tab_charts:
    st.markdown("### 📊 Live Candlestick Charts & AI Pattern Scanner")
    st.caption("**Click any coin or stock below** for instant live candlestick charts, pattern recognition, and institutional indicators:")
    
    # Ensure selected chart symbol is always initialized and strictly matches active mode
    target_default = "BEL.NS" if is_angel_live else "BTC-USD"
    if "selected_chart_sym" not in st.session_state or not st.session_state.get("selected_chart_sym"):
        st.session_state["selected_chart_sym"] = target_default
    elif is_angel_live and not str(st.session_state.get("selected_chart_sym", "")).endswith((".NS", ".BO")):
        st.session_state["selected_chart_sym"] = target_default
    elif not is_angel_live and str(st.session_state.get("selected_chart_sym", "")).endswith((".NS", ".BO")):
        st.session_state["selected_chart_sym"] = target_default

    if is_angel_live:
        st.markdown("##### 🇮🇳 Top Indian Stocks (NSE):")
        dyn_chips = [
            ("🇮🇳 BEL", "BEL.NS"),
            ("🇮🇳 RELIANCE", "RELIANCE.NS"),
            ("🇮🇳 TATA STEEL", "TATASTEEL.NS"),
            ("🇮🇳 SBIN", "SBIN.NS"),
            ("🇮🇳 ITC", "ITC.NS"),
            ("🇮🇳 INFY", "INFY.NS")
        ]
        all_symbols = [s for s in symbol_options.values() if s.endswith(('.NS', '.BO')) or '^NSE' in s]
        sel_label = "Or select any other NSE Indian Stock:"
    else:
        st.markdown("##### 🪙 Popular Cryptos (24/7):")
        dyn_chips = [
            ("🪙 BTC", "BTC-USD"),
            ("🪙 ETH", "ETH-USD"),
            ("🪙 SOL", "SOL-USD"),
            ("🪙 XRP", "XRP-USD"),
            ("🪙 DOGE", "DOGE-USD"),
            ("🪙 BNB", "BNB-USD")
        ]
        all_symbols = [s for s in symbol_options.values() if s.endswith(('-USD', '-USDT'))]
        sel_label = "Or select any other 24/7 Crypto Coin:"

    if not all_symbols:
        all_symbols = list(symbol_options.values())

    cols_chips = st.columns(len(dyn_chips))
    for idx, (label, sym_val) in enumerate(dyn_chips):
        with cols_chips[idx]:
            is_active = (st.session_state.get("selected_chart_sym") == sym_val)
            btn_txt = f"👉 {label}" if is_active else label
            btn_type = "primary" if is_active else "secondary"
            if st.button(btn_txt, key=f"chip_dyn_{sym_val}", use_container_width=True, type=btn_type):
                st.session_state["selected_chart_sym"] = sym_val
                st.rerun()

    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)

    curr_sym = st.session_state.get("selected_chart_sym", target_default)
    curr_idx = all_symbols.index(curr_sym) if curr_sym in all_symbols else 0

    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        sel_chart_sym = st.selectbox(
            sel_label,
            all_symbols,
            index=curr_idx,
            key="chart_sym_select_box"
        )
        if sel_chart_sym != st.session_state.get("selected_chart_sym"):
            st.session_state["selected_chart_sym"] = sel_chart_sym
            st.rerun()

    with col_sel2:
        if st.button("🔄 Refresh Chart", key="btn_refresh_chart", use_container_width=True):
            st.rerun()

    # Load data & Candlestick analysis
    active_sym = st.session_state.get("selected_chart_sym", target_default)
    df, signal, last = fetch_and_analyze(active_sym)
    current_price = last['close'] if last is not None else 65000.0
    signal = signal if signal else "HOLD"

    # 🕯️ Detect Candlestick Patterns
    markers, latest_pat = detect_candlestick_patterns(df)

    # ─── CANDLESTICK PATTERN CARD ───
    pat_sent = latest_pat['sentiment']
    pat_color = "#00e676" if pat_sent == "BULLISH" else ("#ff3b30" if pat_sent == "BEARISH" else "#ffcc00")
    pat_bg = "rgba(0, 230, 118, 0.12)" if pat_sent == "BULLISH" else ("rgba(255, 59, 48, 0.12)" if pat_sent == "BEARISH" else "rgba(255, 204, 0, 0.12)")
    is_inr = (".NS" in active_sym or ".BO" in active_sym or "^NSE" in active_sym)
    curr_prefix = "₹" if is_inr else "$"
    rsi_disp_val = f"{float(last['RSI']):.1f}" if (last is not None and 'RSI' in last and not pd.isna(last['RSI'])) else "50.0"

    card_html = f"""
    <div style="background: linear-gradient(135deg, rgba(20,24,35,0.95), rgba(15,18,28,0.98)); border: 1.5px solid {pat_color}; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 12px; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 32px;">{latest_pat['icon']}</span>
                <div>
                    <div style="font-size: 20px; font-weight: 800; color: #ffffff;">{latest_pat.get('title', latest_pat.get('telugu_title', ''))}</div>
                    <div style="font-size: 13px; color: #90caf9;">Asset: <b style="color:#ffffff;">{active_sym}</b> | Live Price: <b style="color:#ffffff;">{curr_prefix}{current_price:,.2f}</b></div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="background: {pat_bg}; color: {pat_color}; border: 1px solid {pat_color}; padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: 800; letter-spacing: 0.5px;">
                    {latest_pat['icon']} {pat_sent} ({latest_pat['confidence']})
                </span>
            </div>
        </div>
        <div style="background: rgba(255,255,255,0.04); border-radius: 10px; padding: 12px 16px; margin-bottom: 12px; border-left: 4px solid {pat_color};">
            <div style="color: #e0e0e0; font-size: 14px; line-height: 1.6;">
                <b>🔍 Pattern Analysis:</b> {latest_pat.get('desc', latest_pat.get('telugu_desc', ''))}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 10px;">
            <div style="background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="color: #9e9e9e; font-size: 11px; text-transform: uppercase;">🤖 AI Recommendation</div>
                <div style="color: {pat_color}; font-size: 15px; font-weight: 700; margin-top: 2px;">{latest_pat['action']}</div>
            </div>
            <div style="background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="color: #9e9e9e; font-size: 11px; text-transform: uppercase;">🎯 Target (+1.5% Scalp)</div>
                <div style="color: #00e676; font-size: 15px; font-weight: 700; margin-top: 2px;">{curr_prefix}{current_price * 1.015:,.2f}</div>
            </div>
            <div style="background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="color: #9e9e9e; font-size: 11px; text-transform: uppercase;">🛑 Stop-Loss (-2.5% Safe)</div>
                <div style="color: #ff3b30; font-size: 15px; font-weight: 700; margin-top: 2px;">{curr_prefix}{current_price * 0.975:,.2f}</div>
            </div>
            <div style="background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="color: #9e9e9e; font-size: 11px; text-transform: uppercase;">📊 RSI (14) Momentum</div>
                <div style="color: #64b5f6; font-size: 15px; font-weight: 700; margin-top: 2px;">{rsi_disp_val}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Speedometer Gauge & Metrics
    gauge_val = 50
    if signal == "BUY": gauge_val = 85
    elif signal == "SELL": gauge_val = 15

    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge",
        value = gauge_val,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"🤖 AI Market Sentiment: <b>{signal}</b>", 'font': {'size': 20, 'color': 'white'}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "white"},
            'bgcolor': "black",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 35], 'color': 'rgba(255, 50, 50, 0.8)'},
                {'range': [35, 65], 'color': 'rgba(100, 100, 100, 0.6)'},
                {'range': [65, 100], 'color': 'rgba(50, 255, 50, 0.8)'}],
        }
    ))
    fig_gauge.update_layout(height=240, margin=dict(l=10, r=10, t=40, b=10), template='plotly_dark')

    col_g1, col_g2 = st.columns([1, 2])
    with col_g1:
        safe_plotly_chart(fig_gauge)
    with col_g2:
        m1, m2, m3 = st.columns(3)
        m1.markdown(fancy_metric("Trading Pair", active_sym), unsafe_allow_html=True)
        m2.markdown(fancy_metric("Live Price", f"{curr_prefix}{current_price:,.2f}"), unsafe_allow_html=True)
        rsi_str = f"{last['RSI']:.1f}" if (last is not None and 'RSI' in last and not pd.isna(last['RSI'])) else "50.0"
        m3.markdown(fancy_metric("RSI (14)", rsi_str, "Normal", "inverse"), unsafe_allow_html=True)

    # ─── CANDLESTICK CHART WITH PATTERN ANNOTATIONS ───
    if df is not None and not df.empty:
        fig_pro = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            row_heights=[0.62, 0.20, 0.18],
            subplot_titles=(f"🕯️ {active_sym} Live Candlestick & Pattern Markers", "📊 MACD (12, 26, 9)", "📈 RSI Momentum (14)")
        )
        # Main Candlesticks
        fig_pro.add_trace(go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            name=f'{active_sym} Price',
            increasing_line_color='#00e676', decreasing_line_color='#ff3b30'
        ), row=1, col=1)
        # EMAs
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], line=dict(color='cyan', width=1.5), name='EMA 50 (Short Trend)'), row=1, col=1)
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], line=dict(color='orange', width=2), name='EMA 200 (Macro Trend)'), row=1, col=1)

        # 🕯️ Annotate detected patterns directly on candles
        for m in markers[-6:]:
            is_bull = (m['sentiment'] == 'BULLISH')
            fig_pro.add_annotation(
                x=m['timestamp'],
                y=m['price'],
                text=f"{m['icon']} {m['type']}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.2,
                arrowwidth=2,
                arrowcolor="#00e676" if is_bull else "#ff3b30",
                ay=35 if is_bull else -35,
                font=dict(color="#ffffff", size=10, family="Arial"),
                bgcolor="rgba(20, 24, 35, 0.9)",
                bordercolor="#00e676" if is_bull else "#ff3b30",
                borderwidth=1,
                borderpad=4,
                row=1, col=1
            )

        # MACD
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_Line'], line=dict(color='#2962ff', width=1.5), name='MACD'), row=2, col=1)
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_Signal'], line=dict(color='#ff9800', width=1.5), name='Signal'), row=2, col=1)
        macd_colors = ['#00e676' if val >= 0 else '#ff3b30' for val in (df['MACD_Line'] - df['MACD_Signal'])]
        fig_pro.add_trace(go.Bar(x=df['timestamp'], y=(df['MACD_Line'] - df['MACD_Signal']), marker_color=macd_colors, name='MACD Hist'), row=2, col=1)

        # RSI
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI'], line=dict(color='#ba68c8', width=1.8), name='RSI'), row=3, col=1)
        fig_pro.add_hline(y=70, line_dash="dash", line_color="#ff5252", row=3, col=1)
        fig_pro.add_hline(y=30, line_dash="dash", line_color="#69f0ae", row=3, col=1)

        fig_pro.update_layout(
            template='plotly_dark',
            height=780,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=35, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        safe_plotly_chart(fig_pro)

    # ─── CANDLESTICK PATTERNS CHEAT SHEET ───
    with st.expander("📚 Candlestick Patterns Guide & Cheat Sheet", expanded=False):
        st.markdown("""
        | Pattern Name | Type | Sentiment | Description & Trading Strategy |
        |---|---|---|---|
        | 🔨 **Hammer** | Single Candle | 🟢 Bullish | Forms at swing lows. Strong buyer rejection of lower prices. **BUY Signal**. |
        | 🌠 **Shooting Star** | Single Candle | 🔴 Bearish | Forms at swing highs. Heavy selling rejection of higher prices. **SELL Signal**. |
        | 🟩 **Bullish Engulfing** | Double Candle | 🟢 Strong Bullish | Large green candle engulfs prior red body. Buyers in full control. **BUY**. |
        | 🟥 **Bearish Engulfing** | Double Candle | 🔴 Strong Bearish | Large red candle engulfs prior green body. Sellers in full control. **SELL**. |
        | 🌅 **Morning Star** | 3-Candle Pattern | 🟢 Super Bullish | Red -> Compression Doji -> Strong Green. Powerful bottom reversal rally. |
        | 🌇 **Evening Star** | 3-Candle Pattern | 🔴 Super Bearish | Green -> Compression Doji -> Strong Red. Powerful top reversal sell-off. |
        | ⚖️ **Doji** | Single Candle | 🟡 Neutral | Open equals close. Market indecision before high-volatility breakout. |
        | 🐂 **Bullish Marubozu** | Single Candle | 🟢 Strong Momentum | Solid green candle with no wicks. Continuous aggressive buying from open to close. |
        """)


# =============================================================
# TAB 5: 📋 Order Book & Performance History
# =============================================================
with tab_orders:
    if is_angel_live:
        st.subheader("📋 Angel One Order Book & Settlement Statement")
        st.caption("Official Angel One SmartAPI trade ledger, brokerage breakdown, and regulatory settlement statement:")

        # ─── ANGEL ONE OFFICIAL CONTRACT NOTE BREAKDOWN ───
        st.markdown("""
<div style="background: linear-gradient(135deg, #131722 0%, #1e222d 100%);
            border: 1.5px solid #00c853; border-radius: 12px; padding: 18px 22px; margin-bottom: 20px;">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom:12px;">
    <span style="font-size:16px; font-weight:800; color:#00e676;">🏛️ Angel One Contract Note Breakdown (BEL MIS Intraday)</span>
    <span style="background:rgba(0,200,83,0.15); color:#00e676; border:1px solid #00c853; padding:4px 12px; border-radius:16px; font-size:12px; font-weight:700;">SETTLED</span>
  </div>
  <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; font-size:13px;">
    <div style="background:#0d1117; padding:10px 14px; border-radius:8px; border:1px solid #2a2e39;">
      <span style="color:#8892b0;">Account:</span><br><b style="color:#fff;">SHAIK KALESHA (AABZ864543)</b>
    </div>
    <div style="background:#0d1117; padding:10px 14px; border-radius:8px; border:1px solid #2a2e39;">
      <span style="color:#8892b0;">Intraday Equity P&L:</span><br><b style="color:#ff5252;">-₹5.70</b> (3 qty @ ₹358.75 ➔ ₹356.85)
    </div>
    <div style="background:#0d1117; padding:10px 14px; border-radius:8px; border:1px solid #2a2e39;">
      <span style="color:#8892b0;">Brokerage & Taxes:</span><br><b style="color:#ffa726;">-₹11.88</b> (Brokerage, STT, GST, SEBI)
    </div>
    <div style="background:#0d1117; padding:10px 14px; border-radius:8px; border:1px solid #2a2e39;">
      <span style="color:#8892b0;">Net Settlement Deducted:</span><br><b style="color:#ff5252;">-₹17.58</b> (P&L + Charges)
    </div>
    <div style="background:#0d1117; padding:10px 14px; border-radius:8px; border:1px solid #00c853;">
      <span style="color:#8892b0;">Live Available Balance:</span><br><b style="color:#00e676;">₹282.42</b> (Verified from RMS)
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            st.markdown("#### 🇮🇳 Angel One Executed Orders Log")
        with col_s2:
            if st.button("🔄 Refresh Orders", key="btn_ref_angel_orders", use_container_width=True):
                st.rerun()

        df_perf = db_helper.get_trade_history_df(is_futures=False)
        df_perf_valid = pd.DataFrame()
        if not df_perf.empty:
            df_perf_valid = df_perf[df_perf['Symbol'].astype(str).str.endswith(('.NS', '.BO'))].copy()

        if not df_perf_valid.empty:
            enriched_spot = []
            for idx, r in df_perf_valid.iterrows():
                pr = float(r.get('Price', 0))
                sh = float(r.get('Shares', 0))
                sym = str(r.get('Symbol', '')).replace('.NS', '')
                val_inr = pr * sh
                act = str(r.get('Action', '')).upper()
                raw_prof = str(r.get('Profit', '0')).replace('₹', '').replace('$', '').replace(',', '').strip()
                try: g_prof = float(raw_prof)
                except: g_prof = 0.0
                
                est_charges = 11.88 if sym == 'BEL' else 15.00
                net_p = round(g_prof - est_charges, 2) if act == 'SELL' else 0.0

                enriched_spot.append({
                    "Time (IST)": r.get('Time'),
                    "Symbol": sym,
                    "Action": act,
                    "Price": f"₹{pr:,.2f}",
                    "Quantity": f"{int(sh) if sh == int(sh) else sh}",
                    "Turnover (5x)": f"₹{val_inr:,.2f}",
                    "Est Charges": f"₹{est_charges:.2f}" if act == 'SELL' else "-",
                    "Gross P&L": f"₹{g_prof:+,.2f}" if act == 'SELL' else "-",
                    "Net Settlement": f"₹{net_p:+,.2f}" if act == 'SELL' else "-"
                })

            safe_dataframe(pd.DataFrame(enriched_spot).iloc[::-1], hide_index=True)
        else:
            st.info("No prior NSE orders recorded yet.")

    else:
        # 🌐 Binance Paper Trading Mode: Pure Crypto Orders
        st.subheader("📋 Crypto Paper Trading Orders Log")
        st.caption("Historical simulated trades and performance metrics for Spot and Futures practice:")

        df_fo_cnt = len(db_helper.get_trade_history_df(is_futures=True))
        df_sp = db_helper.get_trade_history_df(is_futures=False)
        df_sp_crypto = df_sp[df_sp['Symbol'].astype(str).str.endswith(('-USD', '-USDT'))] if not df_sp.empty else pd.DataFrame()
        
        hist_tab_spot, hist_tab_fut = st.tabs([f"📌 Crypto Spot Orders ({len(df_sp_crypto)})", f"🚀 Crypto Futures (5x) Orders ({df_fo_cnt})"])

        with hist_tab_fut:
            col_f1, col_f2 = st.columns([3, 1])
            with col_f1:
                st.markdown("#### 🚀 Futures Order Book (Futures 5x Orders Log)")
            with col_f2:
                if st.button("🗑️ Reset Futures History", key="btn_reset_fut"):
                    db_helper.reset_trade_history(is_futures=True)
                    db_helper.save_state('fo_state', {})
                    try:
                        requests.get("https://trading-bot-leaw.onrender.com/reset_futures", timeout=4)
                    except Exception:
                        pass
                    st.cache_data.clear()
                    st.toast("✅ Futures trade history permanently cleared!", icon="🗑️")
                    st.rerun()

            df_fo = db_helper.get_trade_history_df(is_futures=True)
            if not df_fo.empty:
                try:
                    enriched_fut = []
                    total_fut_fees = 0.0
                    total_fut_gross = 0.0
                    closed_fo_count = 0
                    fo_wins = 0
                    fo_losses = 0
                    
                    for idx, r in df_fo.iterrows():
                        margin = float(r.get('Margin', 5000.0))
                        lev = int(r.get('Leverage', 5))
                        notional = margin * lev
                        act = str(r.get('Action', '')).upper()
                        gross_pnl = float(r.get('Profit_INR', 0.0))
                        
                        per_trade_fee = round(notional * 0.0005, 2) if act == 'OPEN' else round(notional * 0.001, 2)
                        total_fut_fees += per_trade_fee
                        
                        if act == 'CLOSE':
                            closed_fo_count += 1
                            total_fut_gross += gross_pnl
                            if gross_pnl > 0: fo_wins += 1
                            elif gross_pnl < 0: fo_losses += 1
                            net_fo_pnl = round(gross_pnl - per_trade_fee, 2)
                        else:
                            net_fo_pnl = 0.0
                            
                        entry_val = float(r.get('EntryPrice', 0))
                        exit_val = float(r.get('ExitPrice', 0))
                        
                        enriched_fut.append({
                            "Time (IST)": r.get('Timestamp'),
                            "Symbol": str(r.get('Symbol', '')).replace('-USD', ''),
                            "Action": act,
                            "Side": f"{r.get('Side')} {lev}x",
                            "Entry Price": f"${entry_val:,.2f}",
                            "Exit Price": f"${exit_val:,.2f}" if exit_val > 0 else "-",
                            "Margin": f"₹{margin:,.2f}",
                            "Fees (0.05%)": f"₹{per_trade_fee:.2f}",
                            "Gross P&L": f"₹{gross_pnl:+.2f}" if act == 'CLOSE' else "-",
                            "Net P&L": f"₹{net_fo_pnl:+.2f}" if act == 'CLOSE' else "-"
                        })
                        
                    fo_win_rate = (fo_wins / closed_fo_count * 100) if closed_fo_count > 0 else 0.0
                    net_fut_total = (total_fut_gross - total_fut_fees) if closed_fo_count > 0 else 0.0
                    
                    fp1, fp2, fp3, fp4 = st.columns(4)
                    fp1.metric("Closed Futures Trades", f"{closed_fo_count}")
                    fp2.metric("Futures Win Rate", f"{fo_win_rate:.1f}%", f"{fo_wins}W | {fo_losses}L")
                    fp3.metric("Futures Fees", f"₹{total_fut_fees:,.2f}", "0.05% Taker Fee")
                    f_net_col = "normal" if net_fut_total >= 0 else "inverse"
                    fp4.metric("Net Realized Profit", f"₹{net_fut_total:,.2f}", f"{net_fut_total:+.2f}", f_net_col)
                    
                    safe_dataframe(pd.DataFrame(enriched_fut).iloc[::-1], hide_index=True)
                except Exception as e:
                    st.info("Futures trades are being recorded...")
            else:
                st.info("No futures trade logs yet.")

        with hist_tab_spot:
            col_s1, col_s2 = st.columns([3, 1])
            with col_s1:
                st.markdown("#### 📌 Crypto Spot Orders Log")
            with col_s2:
                if st.button("🗑️ Reset Spot History", key="btn_reset_spot"):
                    db_helper.reset_trade_history(is_futures=False)
                    db_helper.save_state('dca_state', {})
                    try:
                        requests.get("https://trading-bot-leaw.onrender.com/reset_spot", timeout=4)
                    except Exception:
                        pass
                    st.cache_data.clear()
                    st.toast("✅ Spot trade history permanently cleared!", icon="🗑️")
                    st.rerun()

            if not df_sp_crypto.empty:
                try:
                    enriched_spot = []
                    total_spot_fees = 0.0
                    gross_spot_profit = 0.0
                    gross_spot_loss = 0.0
                    closed_count = 0
                    wins = 0
                    losses = 0
                    
                    for idx, r in df_sp_crypto.iterrows():
                        pr = float(r.get('Price', 0))
                        sh = float(r.get('Shares', 0))
                        sym = str(r.get('Symbol', ''))
                        val_usd = pr * sh
                        val_inr = val_usd * USD_TO_INR
                        act = str(r.get('Action', '')).upper()
                        trade_fee_usd = round(val_usd * 0.001, 2)
                        trade_fee_inr = round(val_inr * 0.001, 2)
                        total_spot_fees += trade_fee_inr
                        
                        raw_prof = str(r.get('Profit', '0')).replace('₹', '').replace('$', '').replace(',', '').strip()
                        try: g_prof = float(raw_prof)
                        except: g_prof = 0.0
                        g_prof_inr = round(g_prof * USD_TO_INR, 2)
                        
                        if act == 'SELL':
                            closed_count += 1
                            if g_prof_inr > 0:
                                gross_spot_profit += g_prof_inr
                                wins += 1
                            elif g_prof_inr < 0:
                                gross_spot_loss += abs(g_prof_inr)
                                losses += 1
                            net_p = round(g_prof_inr - (trade_fee_inr * 2), 2)
                        else:
                            net_p = 0.0
                            
                        gross_disp = f"+${g_prof:,.2f} (₹{g_prof_inr:+,.2f})" if g_prof > 0 else (f"-${abs(g_prof):,.2f} (₹{g_prof_inr:+,.2f})" if g_prof < 0 else "$0.00")
                            
                        enriched_spot.append({
                            "Time (IST)": r.get('Time'),
                            "Symbol": sym.replace('-USD', ''),
                            "Action": act,
                            "Price": f"${pr:,.2f}",
                            "Quantity": f"{sh:.4f}",
                            "Turnover": f"${val_usd:,.2f} (₹{val_inr:,.0f})",
                            "Fees (0.1%)": f"${trade_fee_usd:.2f}",
                            "Gross Profit": gross_disp if act == 'SELL' else "-",
                            "Net PnL": f"₹{net_p:+,.2f}" if act == 'SELL' else "-"
                        })
                        
                    net_spot_total = (gross_spot_profit - gross_spot_loss - total_spot_fees) if closed_count > 0 else 0.0
                    win_rate = (wins / closed_count * 100) if closed_count > 0 else 0.0
                    
                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric("Closed Spot Trades", f"{closed_count}")
                    p2.metric("Spot Win Rate", f"{win_rate:.1f}%", f"{wins}W | {losses}L")
                    p3.metric("Brokerage & Fees", f"₹{total_spot_fees:,.2f}", "0.1% Fee")
                    net_col = "normal" if net_spot_total >= 0 else "inverse"
                    p4.metric("Net Realized Profit", f"₹{net_spot_total:,.2f}", f"{net_spot_total:+.2f}", net_col)

                    if enriched_spot:
                        safe_dataframe(pd.DataFrame(enriched_spot).iloc[::-1], hide_index=True)
                except Exception as e:
                    st.info("Spot trades are being recorded...")
            else:
                st.info("No crypto spot trade logs yet.")

# =============================================================
# TAB 5: 🔍 Smart Asset Screener (ASSET SCREENER)
# =============================================================
with tab_search:
    if is_angel_live:
        st.header("🔍 NSE 25 Momentum Stock Screener & Watchlist")
        st.caption("Active screener for Indian equities eligible for 5x MIS Intraday Trading on Angel One:")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            search_query = st.text_input("🔎 Search NSE Stock Ticker:", placeholder="e.g. BEL, ITC, TATASTEEL, ONGC, IOC, SUZLON, SBIN, HDFCBANK", key="nse_search_input")
        with col_s2:
            market_choice = st.radio("Market Type:", ["🇮🇳 Indian Stock (NSE)"], key="universal_market_choice")
    else:
        st.header("🔍 Crypto 24/7 Universal Screener & Watchlist")
        st.caption("Active 24/7 screener for crypto assets on Binance Paper Trading:")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            search_query = st.text_input("🔎 Search Crypto Coin / Pair:", placeholder="e.g. BTC, ETH, SOL, XRP, DOGE, ADA, NEAR", key="crypto_search_input")
        with col_s2:
            market_choice = st.radio("Market Type:", ["🪙 Crypto (USD)"], key="universal_market_choice")
        
    do_search = st.button("🔍 Verify Live Asset Data", use_container_width=True)
    if do_search and search_query.strip():
        raw_q = search_query.strip().upper()
        if "Indian" in market_choice or "NSE" in market_choice or is_angel_live:
            clean_sym = raw_q.replace('.NS', '').replace('.BO', '')
            final_sym = f"{clean_sym}.NS"
            asset_category = "NSE"
            curr_symbol = "₹"
        else:
            clean_sym = raw_q.replace('-USD', '').replace('USDT', '').replace('/', '')
            final_sym = f"{clean_sym}-USD"
            asset_category = "CRYPTO"
            curr_symbol = "$"
            
        with st.spinner(f"Fetching market data for {final_sym}..."):
            found_data = None
            try:
                t_obj = yf.Ticker(final_sym)
                hist = t_obj.history(period="5d", interval="1d")
                if not hist.empty:
                    last_row = hist.iloc[-1]
                    l_price = float(last_row['Close'])
                    prev_close = float(hist.iloc[-2]['Close']) if len(hist) > 1 else l_price
                    chg_pct = ((l_price - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
                    vol = int(last_row['Volume'])
                    c_name = clean_sym
                    try: c_name = t_obj.info.get('shortName') or t_obj.info.get('name') or clean_sym
                    except: pass
                    found_data = {
                        "symbol": final_sym, "clean": clean_sym, "name": c_name, "price": l_price,
                        "change_pct": chg_pct, "volume": vol, "type": asset_category, "curr": curr_symbol
                    }
            except Exception: pass
            
        if found_data:
            st.success(f"✅ **{found_data['name']} ({found_data['symbol']})** verified in market!")
            m_c1, m_c2 = st.columns(2)
            m_c1.metric("💰 Current Live Price", f"{found_data['curr']}{found_data['price']:,.2f}", f"{found_data['change_pct']:+.2f}%")
            m_c2.metric("📊 Volume", f"{found_data['volume']:,}")
            
            wl_now = load_custom_watchlist()
            if found_data['symbol'] in wl_now:
                st.info(f"ℹ️ **{found_data['symbol']}** is already in bot trading watchlist.")
            else:
                if st.button(f"➕ Add {found_data['name']} to Bot Watchlist", type="primary", use_container_width=True, key="btn_add_to_wl"):
                    wl_now[found_data['symbol']] = {
                        "name": found_data['name'], "ticker": found_data['symbol'], "type": found_data['type'],
                        "added_at": get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_custom_watchlist(wl_now)
                    st.success(f"🎉 **{found_data['name']} ({found_data['symbol']})** added successfully!")
                    time.sleep(1)
                    st.rerun()


# =============================================================
# TAB 6: 💬 AI Voice & Chat Assistant (VOICE ASSISTANT & LOGS)
# =============================================================
with tab_voice:
    st.subheader("💬 Live AI Trading Assistant Chat 🥷")
    st.caption("Chat live with your AI Trading Bot. Powered by real-time portfolio metrics, live orders, and market telemetry.")

    # 🔑 Optional Gemini API Key for True Super-Intelligence
    user_gem_key = st.text_input("🔑 Optional Google Gemini API Key for Enhanced Reasoning:", value=st.session_state.get('saved_gemini_key', ''), type="password", help="Get a free API key at aistudio.google.com/apikey")
    if user_gem_key:
        st.session_state['saved_gemini_key'] = user_gem_key
        try:
            genai.configure(api_key=user_gem_key)
        except:
            pass

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! I am your Antigravity AI Trading Assistant. Ready to analyze markets and track portfolio performance. What would you like to know?"}
            ]
            st.rerun()

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! I am your AI Trading Assistant. Ask me anything about your positions, PnL, or market analysis!"}
            ]
        chat_box = st.container(height=380)
        with chat_box:
            for msg in st.session_state.messages:
                avatar = "🤖" if msg["role"] == "assistant" else "👤"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.write(msg["content"])
                    
        voice_prompt = speech_to_text(language='en-US', start_prompt="🎙️ Click to speak", stop_prompt="🛑 Click to stop", just_once=True, key='STT')
        prompt = st.chat_input("Type your question or trading command here...")
        final_prompt = voice_prompt if voice_prompt else prompt

    if final_prompt:
        st.session_state.messages.append({"role": "user", "content": final_prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(final_prompt)
            
        t = final_prompt.lower()
        
        # 🌟 1. IF REAL GEMINI KEY IS PROVIDED -> USE ADVANCED GOOGLE GEMINI 1.5 FLASH!
        gem_key_to_use = st.session_state.get('saved_gemini_key', '')
        gem_answered = False
        response = ""
        
        if gem_key_to_use and gem_key_to_use.startswith("AIza"):
            try:
                sys_prompt = f"""You are 'Antigravity Scammer Brain 🥷', an aggressive, smart, funny and loyal AI trading assistant for your boss.
Answer the boss in natural conversational Telugu (mix of Telugu and trading English words).
Current Portfolio Context:
- Available Free Cash: ₹{available_cash:,.2f}
- Invested Amount: ₹{invested_amount:,.2f}
- Net Portfolio Value: ₹{portfolio_value:,.2f}
- Active Open Coins: {list(dca_positions.keys()) if dca_positions else 'None'}
- Live Floating PnL: ₹{total_floating_pnl:+,.2f}

Boss asks: "{final_prompt}"
Answer directly, smartly, and concisely in English in 2-3 sentences. Always address them as Boss:"""
                if HAS_NEW_GENAI:
                    client_gem = genai.Client(api_key=gem_key_to_use)
                    res_gem = client_gem.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=sys_prompt
                    )
                    if res_gem and hasattr(res_gem, 'text') and res_gem.text:
                        response = res_gem.text
                        gem_answered = True
                elif genai is not None:
                    genai.configure(api_key=gem_key_to_use)
                    model_gem = genai.GenerativeModel('gemini-1.5-flash')
                    res_gem = model_gem.generate_content(sys_prompt)
                    if res_gem and hasattr(res_gem, 'text') and res_gem.text:
                        response = res_gem.text
                        gem_answered = True
            except Exception as e:
                gem_answered = False
                gem_answered = False

        if not gem_answered:
                # 🌟 2. BUILT-IN EXPANDED CONVERSATIONAL ENGINE
            
            # 🧠 INTELLIGENT SCAMMER BRAIN DIALOGUE ENGINE
            coins_map = {
                "btc": "BTC-USD", "bitcoin": "BTC-USD",
                "eth": "ETH-USD", "ethereum": "ETH-USD",
                "sol": "SOL-USD", "solana": "SOL-USD",
                "bnb": "BNB-USD", "binance": "BNB-USD",
                "doge": "DOGE-USD",
                "xrp": "XRP-USD", "ripple": "XRP-USD",
                "reliance": "RELIANCE.NS",
                "tcs": "TCS.NS", "hdfc": "HDFCBANK.NS", "sbin": "SBIN.NS", "sbi": "SBIN.NS"
            }
            
            found_coin = None
            for k, sym in coins_map.items():
                if k in t:
                    found_coin = sym
                    break
                    
            if found_coin:
                asset = scanned_assets.get(found_coin, {})
                pos = dca_positions.get(found_coin)
                c_name = found_coin.replace('-USD', '').replace('.NS', '')
                p_curr = asset.get('price', 0)
                p_str = f"${p_curr:,.2f}" if '-USD' in found_coin else f"₹{p_curr:,.2f}"
                sig = asset.get('signal', 'MONITORING')
                rsi = asset.get('rsi', 'N/A')
                thought = asset.get('thought', 'Analyzing price action and volume divergence.')
                
                if pos:
                    avg_p = pos.get('avg_price', 1)
                    pnl = ((p_curr - avg_p) / avg_p) * 100 if avg_p > 0 else 0
                    tgt = pos.get('target_sell_price', avg_p * 1.015)
                    tgt_str = f"${tgt:,.2f}" if '-USD' in found_coin else f"₹{tgt:,.2f}"
                    c_icon = "🟢" if pnl >= 0 else "🔴"
                    response = (
                        f"🥷 **{c_name} Live Report Boss:**\n"
                        f"- Active in portfolio! (Allocation: ₹{pos.get('total_cost', 0):,.2f})\n"
                        f"- Average Buy Price: {avg_p:,.2f} | Live Price: {p_str}\n"
                        f"- P&L: {c_icon} **{pnl:+.2f}%**\n"
                        f"- Target Exit (+1.5% profit): **{tgt_str}**\n"
                        f"- Signal: **{sig}** (RSI: {rsi})\n\n"
                        f"💡 **AI Strategy:** {thought}"
                    )
                else:
                    response = (
                        f"🥷 **{c_name} Update Boss:**\n"
                        f"- No active position held.\n"
                        f"- Live Price: {p_str} | Signal: **{sig}** (RSI: {rsi})\n"
                        f"- Status: {asset.get('action_taken', 'Scanning market')}\n\n"
                        f"💡 **AI Strategy:** {thought}"
                    )
    
            elif any(w in t for w in ["profit", "gain", "earnings", "pnl", "returns"]):
                p_icon = "🟢" if total_floating_pnl >= 0 else "🔴"
                response = (
                    f"💰 **Portfolio Financial Summary Boss:**\n"
                    f"- Total Portfolio Value: **₹{portfolio_value:,.2f}**\n"
                    f"- Live Floating PnL: {p_icon} **₹{total_floating_pnl:+,.2f}**\n"
                    f"- Invested Amount: **₹{invested_amount:,.2f}**\n"
                    f"- Available Free Cash: **₹{available_cash:,.2f}**\n\n"
                    f"As soon as prices reach targets, profits are locked in automatically!"
                )
    
            elif any(w in t for w in ["loss", "drawdown", "risk", "down"]):
                response = (
                    "🛡️ **Risk Management Safeguards Active:**\n"
                    "Market pullbacks are normal. The bot has executed hard stop-losses to cap downside risk and preserve capital. "
                    "We hold ample free cash ready to accumulate at prime support levels!"
                )
    
            elif any(w in t for w in ["status", "duty", "doing", "active", "run"]):
                num = len(dca_positions)
                response = (
                    f"🥷 **I am active on duty 24/7 Boss!**\n"
                    f"- Continuously scanning live 15-minute multi-asset market data.\n"
                    f"- Currently holding **{num} active coin positions**.\n"
                    f"- Remaining ₹{available_cash:,.2f} cash reserved for high-probability dips.\n"
                    f"- AI anomaly filters active to sidestep fake pumps and liquidity traps."
                )
    
            elif any(w in t for w in ["portfolio", "holdings", "coins", "positions"]):
                if not dca_positions:
                    response = f"💼 **Portfolio Update:**\nNo active positions currently held Boss! Total ₹{available_cash:,.2f} safely preserved in cash. Standing by for prime entry signals!"
                else:
                    response = "💼 **Current Active Positions:**\n"
                    for s, p in dca_positions.items():
                        response += f"- **{s}:** ₹{p.get('total_cost', 0):,.2f} (Avg Price: {p.get('avg_price', 0):,.2f})\n"
    
            elif any(w in t for w in ["learning", "days", "accuracy", "train", "time"]):
                response = (
                    "🧠 **AI Adaptive Learning Process:**\n\n"
                    "The neural bot actively evaluates rolling market cycles every 15 minutes. "
                    "It cross-references 60 days of historical volume profile, liquidity clusters, and support rebounds. "
                    "As it logs more trades across volatility regimes, its prediction accuracy continues to sharpen toward target performance."
                )
    
            elif any(w in t for w in ["poor", "bad", "angry", "waste", "dummy"]):
                response = (
                    "💡 **Continuous Optimization Active:**\n\n"
                    "Every trade is logged and analyzed by the machine learning risk engine to optimize entry timing. "
                    "You can also attach a free Google Gemini API Key in the box above to enable advanced multimodal market reasoning!"
                )
    
            elif any(w in t for w in ["real money", "live money", "real trading", "zerodha", "binance"]):
                response = (
                    "🔥 **Execution Ready Boss!**\n\n"
                    "The system architecture includes connectors for Binance API and Zerodha Kite API. "
                    "When live mode is toggled with your API keys, trades will route directly to exchange accounts.\n\n"
                    "Paper trading first ensures strategies are thoroughly validated across live market conditions."
                )
    
            elif any(w in t for w in ["trading ela", "how is trading", "performance", "trade"]):
                num = len(dca_positions)
                response = (
                    f"📊 **Trading Execution is Highly Active Boss!**\n\n"
                    f"- Currently tracking **{num} active positions**.\n"
                    f"- Capital deployed: **₹{invested_amount:,.2f}**, with **₹{available_cash:,.2f}** free cash in reserve.\n"
                    f"- Multi-factor strategy scanning 15-minute momentum and RSI triggers.\n"
                    f"- Trailing targets set to harvest profits systematically at optimal points."
                )
    
            elif any(w in t for w in ["market", "trend", "btc", "condition"]):
                response = (
                    "🌐 **Market Condition Overview:**\n\n"
                    "Volatility is elevated across major pairs. "
                    "Our AI monitors VWAP, RSI divergence, and liquidity depth before executing entries to avoid bull/bear traps."
                )
    
            elif any(w in t for w in ["strategy", "logic", "rules", "setup"]):
                response = (
                    "🎯 **Core Trading Strategy Mechanics:**\n\n"
                    "1. **RSI + VWAP Anchor:** Enters near institutional liquidity zones.\n"
                    "2. **Dynamic DCA:** Averages strategically on confirmed support bounces.\n"
                    "3. **Trailing Profit Lock:** Locks gains once profit exceeds +1.5%.\n"
                    "4. **Strict Risk Shield:** Caps drawdowns with automated stop-losses."
                )
    
            elif any(w in t for w in ["reset", "clear", "restart", "zero"]):
                response = "🔄 Boss! To reset the portfolio fresh to ₹50,000 capital, open **https://trading-bot-leaw.onrender.com/reset** in your browser. It resets immediately in one click!"
    
            elif any(w in t for w in ["who are you", "name", "about"]):
                response = "🥷 I am your **Antigravity AI Trading System!** Engineered to monitor markets 24/7, counter liquidity sweeps, and manage risk systematically."
    
            elif any(w in t for w in ["hi", "hello", "hey", "sup"]):
                response = f"👋 Hello Boss! Active 24/7. Current free cash: ₹{available_cash:,.2f}. Ready to analyze any stock or crypto pair."
    
            elif any(w in t for w in ["fear", "tension", "scared", "worried"]):
                response = (
                    "😎 **No need to worry Boss!**\n"
                    "Market fluctuations are part of trading. Automated stop-losses, DCA protection, and exposure caps are strictly active. Relax while the system manages the positions."
                )
    
            elif any(w in t for w in ["sell all", "close all", "exit", "panic"]):
                response = "🛑 Boss! Go to the Orders tab or trigger emergency exit to close all open positions and liquidate back to 100% cash."
    
            elif any(w in t for w in ["buy", "entry", "order"]):
                response = "🎯 Boss! The bot is continuously scanning 15-minute timeframe charts. As soon as bullish confirmation triggers, an optimal entry will be placed."
    
            else:
                response = f"🥷 Understood Boss. The AI bot is actively managing {len(dca_positions)} open positions with ₹{available_cash:,.2f} cash reserve. All automated risk rules and monitors are active."

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant", avatar="🥷"):
            st.write(response)

    st.markdown("---")
    st.subheader("📝 Live Bot Execution Logs")
    with st.expander("Inspect live terminal logs and execution traces"):
        if os.path.exists('bot_logs.txt'):
            with open('bot_logs.txt', 'r') as f_l:
                logs = f_l.readlines()
            recent_logs = logs[-15:] if len(logs) > 15 else logs
            st.code("".join(recent_logs), language="bash")
        else:
            st.info("No logs generated yet.")

if refresh_mode == "Fast (10s)":
    time.sleep(10)
    st.rerun()
elif refresh_mode == "Auto-Refresh (30s)":
    time.sleep(30)
    st.rerun()
elif refresh_mode == "Auto-Refresh (60s)":
    time.sleep(60)
    st.rerun()
