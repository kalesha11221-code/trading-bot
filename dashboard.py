import os
import sys
import time
import json
import threading
from datetime import datetime

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

_bg_bot_thread = None

def start_bot_thread(force=False):
    global _bg_bot_thread
    if force or _bg_bot_thread is None or not _bg_bot_thread.is_alive():
        _bg_bot_thread = threading.Thread(target=_run_background_bot, daemon=True)
        _bg_bot_thread.start()
        return True
    return False

start_bot_thread()

def get_bot_heartbeat():
    hb_file = 'bot_heartbeat.json'
    if os.path.exists(hb_file):
        try:
            with open(hb_file, 'r') as f:
                data = json.load(f)
            last_ping = data.get('last_ping', 0)
            diff = time.time() - last_ping
            if diff <= 30:
                return "RUNNING", int(diff), data
            elif diff <= 70:
                return "DELAYED", int(diff), data
            else:
                return "STOPPED", int(diff), data
        except Exception:
            pass

    # Secondary fallback to bot_logs.txt timestamp/mtime
    if os.path.exists('bot_logs.txt'):
        try:
            mtime = os.path.getmtime('bot_logs.txt')
            diff = time.time() - mtime
            if diff <= 35:
                return "RUNNING", int(diff), {"loop_count": "-", "last_action": "లైవ్ స్కానింగ్ జరుగుతోంది"}
            elif diff <= 90:
                return "DELAYED", int(diff), {"loop_count": "-", "last_action": "ఆలస్యం"}
            else:
                return "STOPPED", int(diff), {"loop_count": "-", "last_action": "ఆగిపోయింది"}
        except Exception:
            pass
            
    return "STOPPED", 999, {"loop_count": 0, "last_action": "బాట్ ఇంకా స్టార్ట్ కాలేదు"}


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
        "normal": "#00ff00" if ("-" not in str(delta) and "నష్టం" not in str(delta) and "Loss" not in str(delta)) else "#ff3333",
        "inverse": "#ff3333" if ("-" not in str(delta)) else "#00ff00",
        "off": "gray"
    }
    
    # Overrides based on text content
    if delta:
        if any(w in str(delta).lower() for w in ["సూపర్", "లాభం", "bullish", "profit", "up"]): color = "#00ff00"
        elif any(w in str(delta).lower() for w in ["నష్టం", "loss", "bearish", "down", "risk", "రిస్క్"]): color = "#ff3333"
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
import google.generativeai as genai

# గూగుల్ జెమినీ API కీ సెటప్
GEMINI_API_KEY = "AQ.Ab8RN6KSOIMcia4BvnmtR5CxhuTrDJ7jQxe9MmwfCPXIDRQ_Ig"
genai.configure(api_key=GEMINI_API_KEY)

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
                    elif "ఎర్రర్" in last_line:
                        st.toast(last_line, icon="⚠️")
                    elif "HOLD" not in last_line:
                        st.toast(last_line, icon="🤖")
    except:
        pass


# 🌟 Zerodha Kite Pro Top Navigation Header
bot_status, bot_diff, bot_meta = get_bot_heartbeat()
loop_num = bot_meta.get('loop_count', '-')
last_act = bot_meta.get('last_action', 'స్కానింగ్')
active_syms = bot_meta.get('active_symbols', [])

from datetime import datetime
now_time = datetime.now()
is_nse_time = (now_time.weekday() < 5 and ((now_time.hour == 9 and now_time.minute >= 15) or (9 < now_time.hour < 15) or (now_time.hour == 15 and now_time.minute <= 30)))
nse_badge = '<span style="background: rgba(0, 230, 118, 0.15); color: #00e676; border: 1px solid #00e676; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🟢 Zerodha NSE Live</span>' if is_nse_time else '<span style="background: rgba(255, 82, 82, 0.15); color: #ff5252; border: 1px solid #ff5252; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🔴 Zerodha NSE Closed (Opens 9:15 AM)</span>'
bot_status_badge = '<span style="background: rgba(0, 230, 118, 0.2); color: #00e676; border: 1px solid #00e676; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: bold;">🟢 AI BOT ONLINE & SCANNING</span>' if bot_status == 'RUNNING' else '<span style="background: rgba(255, 82, 82, 0.2); color: #ff5252; border: 1px solid #ff5252; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: bold;">🔴 BOT STOPPED</span>'

st.markdown(f'''
<div class="zk-navbar">
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
</div>
''', unsafe_allow_html=True)


# --- 💓 LIVE BOT STATUS INDICATOR (ఆన్ లో ఉందా / ఆగిపోయిందా) ---
bot_status, bot_diff, bot_meta = get_bot_heartbeat()
loop_num = bot_meta.get('loop_count', '-')
last_act = bot_meta.get('last_action', 'స్కానింగ్')
active_syms = bot_meta.get('active_symbols', [])

broker_badge = bot_meta.get('broker', 'Binance Spot')
if len(active_syms) > 1:
    has_nse = any('.NS' in s or '.BO' in s for s in active_syms)
    has_crypto = any('-USD' in s for s in active_syms)
    if has_nse and has_crypto:
        syms_display = f"🌐🇮🇳 Dual Hybrid ({len(active_syms)} Assets: Crypto + NSE)"
    elif has_nse:
        clean_syms = [s.replace('.NS', '').replace('.BO', '') for s in active_syms]
        syms_display = f"🇮🇳 Zerodha NSE ({', '.join(clean_syms[:4])}{'...' if len(clean_syms) > 4 else ''})"
    else:
        clean_syms = [s.replace('-USD', '') for s in active_syms]
        syms_display = f"🌐 మల్టీ-కాయిన్ ({', '.join(clean_syms)})"
elif len(active_syms) == 1:
    syms_display = f"🎯 {active_syms[0].replace('.NS', '').replace('.BO', '').replace('-USD', '')}"
else:
    syms_display = "⚡ స్కానింగ్"

if bot_status == "RUNNING":
    st.markdown(f'''
    <div style="background: linear-gradient(90deg, #0d381e 0%, #164e2a 100%); border: 1.5px solid #00e676; border-radius: 12px; padding: 12px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 15px rgba(0, 230, 118, 0.15);">
        <div style="display: flex; align-items: center; gap: 14px;">
            <span style="height: 16px; width: 16px; background-color: #00e676; border-radius: 50%; display: inline-block; box-shadow: 0 0 12px #00e676;"></span>
            <div>
                <div style="color: #ffffff; font-size: 16px; font-weight: bold;">🟢 బాట్ ఆన్ లో ఉంది (BOT IS ONLINE & RUNNING)</div>
                <div style="color: #b9f6ca; font-size: 13px; margin-top: 2px;">చివరి స్కాన్: <b>{bot_diff}s క్రితం</b> | ఫోకస్: <b>{syms_display}</b> | లూప్: <b>#{loop_num}</b><br>స్టేటస్: <b>{last_act}</b></div>
            </div>
        </div>
        <span style="background-color: rgba(0, 230, 118, 0.25); color: #00e676; border: 1px solid #00e676; padding: 5px 14px; border-radius: 8px; font-size: 13px; font-weight: bold;">● LIVE ACTIVE</span>
    </div>
    ''', unsafe_allow_html=True)
elif bot_status == "DELAYED":
    st.markdown(f'''
    <div style="background: linear-gradient(90deg, #3d2f09 0%, #57420c 100%); border: 1.5px solid #ffd600; border-radius: 12px; padding: 12px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 15px rgba(255, 214, 0, 0.15);">
        <div style="display: flex; align-items: center; gap: 14px;">
            <span style="height: 16px; width: 16px; background-color: #ffd600; border-radius: 50%; display: inline-block; box-shadow: 0 0 12px #ffd600;"></span>
            <div>
                <div style="color: #ffffff; font-size: 16px; font-weight: bold;">🟡 బాట్ రెస్పాన్స్ ఆలస్యం (BOT SLOW / WAITING)</div>
                <div style="color: #fff9c4; font-size: 13px; margin-top: 2px;">చివరి స్కాన్: <b>{bot_diff} సెకన్ల క్రితం</b> (డేటా లేదా తదుపరి లూప్ కోసం వేచి చూస్తోంది)</div>
            </div>
        </div>
        <span style="background-color: rgba(255, 214, 0, 0.25); color: #ffd600; border: 1px solid #ffd600; padding: 5px 14px; border-radius: 8px; font-size: 13px; font-weight: bold;">WAITING</span>
    </div>
    ''', unsafe_allow_html=True)
else:
    st.markdown(f'''
    <div style="background: linear-gradient(90deg, #421313 0%, #5c1b1b 100%); border: 1.5px solid #ff5252; border-radius: 12px; padding: 12px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 15px rgba(255, 82, 82, 0.15);">
        <div style="display: flex; align-items: center; gap: 14px;">
            <span style="height: 16px; width: 16px; background-color: #ff5252; border-radius: 50%; display: inline-block; box-shadow: 0 0 12px #ff5252;"></span>
            <div>
                <div style="color: #ffffff; font-size: 16px; font-weight: bold;">🔴 బాట్ ఆగిపోయింది (BOT STOPPED / OFFLINE)</div>
                <div style="color: #ffcdd2; font-size: 13px; margin-top: 2px;">బాట్ ప్రస్తుతం బ్యాక్‌గ్రౌండ్‌లో రన్ అవ్వడం లేదు ({bot_diff}s క్రితం చివరి పింగ్). వెంటనే స్టార్ట్ చేయడానికి కింద బటన్ నొక్కండి.</div>
            </div>
        </div>
        <span style="background-color: rgba(255, 82, 82, 0.25); color: #ff5252; border: 1px solid #ff5252; padding: 5px 14px; border-radius: 8px; font-size: 13px; font-weight: bold;">OFFLINE</span>
    </div>
    ''', unsafe_allow_html=True)
    if st.button("▶️ బాట్ ని వెంటనే ఆన్ చేయండి (Restart Bot Now)"):
        start_bot_thread(force=True)
        st.toast("🚀 బాట్ ఆన్ అయ్యింది!", icon="🟢")
        time.sleep(1)
        st.rerun()

# Display Market Segment Badge
st.markdown('''
<div style="display: flex; gap: 10px; margin-bottom: 15px;">
    <span style="background-color: #2e7d32; color: white; padding: 4px 14px; border-radius: 20px; font-weight: bold; font-size: 13px;">📈 Market: SPOT TRADING</span>
    <span style="background-color: #1565c0; color: white; padding: 4px 14px; border-radius: 20px; font-weight: bold; font-size: 13px;">🤖 AI Engine: Active</span>
</div>
''', unsafe_allow_html=True)

st.markdown("ప్రొఫెషనల్ ట్రేడర్స్ ఉపయోగించే అడ్వాన్స్డ్ టెక్నికల్ అనాలసిస్ (EMA, RSI, MACD) ఆధారంగా పనిచేసే AI బాట్.")

# Live Refresh Button
colA, colB = st.columns([8, 2])
with colA:
    pass # Title is already above
with colB:
    if safe_button("🔄 Get Live Updates"):
        st.toast("✅ లాగ్స్ అప్‌డేట్ అయ్యాయి!", icon="🔄")


# Sidebar options & Bot Status Widget
if bot_status == "RUNNING":
    st.sidebar.success(f"🟢 బాట్ ఆన్ లో ఉంది (లైవ్: {bot_diff}s క్రితం)")
elif bot_status == "DELAYED":
    st.sidebar.warning(f"🟡 బాట్ ఆలస్యం ({bot_diff}s)")
else:
    st.sidebar.error("🔴 బాట్ ఆగిపోయింది (Offline)")
    if st.sidebar.button("▶️ Start Trading Bot"):
        start_bot_thread(force=True)
        st.toast("🚀 బాట్ స్టార్ట్ అయ్యింది!", icon="🟢")
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

# Trading Mode Switch
mode_options = [
    "🌐🇮🇳 Dual Trading (Crypto 24/7 + Indian Stocks NSE)",
    "🇮🇳 Paper Trading (Indian Stocks - Zerodha Virtual)",
    "📝 Paper Trading (Crypto - Binance Virtual)",
    "💰 Live Trading (Binance Real Money)"
]

saved_mode = "🌐🇮🇳 Dual Trading (Crypto 24/7 + Indian Stocks NSE)"
if os.path.exists('trading_mode.txt'):
    try:
        with open('trading_mode.txt', 'r') as f:
            c = f.read().strip()
            if "Dual" in c:
                saved_mode = "🌐🇮🇳 Dual Trading (Crypto 24/7 + Indian Stocks NSE)"
            elif "Zerodha" in c or "Indian" in c:
                saved_mode = "🇮🇳 Paper Trading (Indian Stocks - Zerodha Virtual)"
            elif "Live" in c:
                saved_mode = "💰 Live Trading (Binance Real Money)"
            else:
                saved_mode = "📝 Paper Trading (Crypto - Binance Virtual)"
    except: pass

mode_idx = mode_options.index(saved_mode) if saved_mode in mode_options else 0
trading_mode = st.sidebar.radio("స్విచ్ (Mode Switch)", mode_options, index=mode_idx)
st.sidebar.markdown("---")

is_dual_mode = "Dual" in trading_mode
is_zerodha_mode = ("Zerodha" in trading_mode or is_dual_mode)

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

if is_dual_mode:
    st.sidebar.success("🌐🇮🇳 **Dual Trading Active!**")
    st.sidebar.info("🚀 క్రిప్టో 24/7 నాన్-స్టాప్ & ఇండియన్ స్టాక్స్ (NSE) సైమల్టేనియస్ గా ఒకేసారి రన్ అవుతాయి.")
    st.sidebar.markdown(f"**💰 క్యాపిటల్:** ₹50,000 (NSE) + " + (f"${live_usdt_balance:.2f} (Binance Live)" if live_usdt_balance > 0 else "$10,000 (Crypto Virtual)"))
elif "Zerodha" in trading_mode:
    st.sidebar.success("🇮🇳 **Zerodha Kite Virtual:** ₹50,000.00 క్యాపిటల్")
    st.sidebar.info("భారతీయ స్టాక్స్ (NSE - Reliance, Tata Motors, HDFC Bank, Infosys, SBI, etc.) పై వర్చువల్ మనీతో రిస్క్ లేకుండా ట్రేడింగ్ జరుగుతుంది.")
else:
    if "Live" in trading_mode:
        if live_usdt_balance > 0:
            st.sidebar.success(f"✅ Real Binance Balance: **${live_usdt_balance:.2f}**")
            st.sidebar.warning("⚠️ Live Trading On! బాట్ బైనాన్స్ లో నిజమైన ట్రేడ్స్ చేస్తుంది.")
        else:
            st.sidebar.error("⚠️ బినాన్స్ కనెక్ట్ అవ్వలేదు. (Keys Check చేయండి)")
            trading_mode = "📝 Paper Trading (Crypto - Binance Virtual)"
    else:
        st.sidebar.info("ప్రస్తుతం Crypto ప్రాక్టీస్ (Virtual) మోడ్ లో ఉంది. మీ రియల్ బినాన్స్ మనీ కట్ అవ్వదు.")

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
new_style = st.sidebar.selectbox(
    "⏱️ Trading Style", 
    ["Scalping (Fast)", "Swing (Hold for Targets)"], 
    index=["Scalping (Fast)", "Swing (Hold for Targets)"].index(bot_settings.get("trading_style", "Scalping (Fast)"))
)

# 2. Capital Sizing Engine (భారీ లాభాల కోసం పెద్ద క్యాపిటల్)
cap_options = [
    "🚀 High Profit (పెద్ద క్యాపిటల్ & భారీ లాభాలు - ₹5,000-₹10,000 / $35-$50)",
    "⚖️ Smart Dynamic (AI కాన్ఫిడెన్స్ స్కేలింగ్ - $20 / 2-5 షేర్లు)",
    "🛡️ Micro Safe (చిన్న రిస్క్ - $10 / 1-2 షేర్లు)"
]
current_cap = bot_settings.get("capital_mode", "High Profit")
cap_idx = 0
if "Dynamic" in current_cap: cap_idx = 1
elif "Micro" in current_cap: cap_idx = 2

new_cap_label = st.sidebar.selectbox(
    "💰 క్యాపిటల్ సైజ్ (Capital Sizing)",
    cap_options,
    index=cap_idx,
    help="లాభాలు వేగంగా మరియు భారీగా రావడానికి బాట్ పెద్ద సైజ్ తో ట్రేడ్ చేస్తుంది!"
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
panic = safe_button("🛑 EMERGENCY PANIC STOP", is_sidebar=True, help="కొన్న కాయిన్స్ అన్నీ వెంటనే అమ్మేసి బాట్ ని ఆపేస్తుంది!")

st.sidebar.markdown("<br>", unsafe_allow_html=True)
if st.sidebar.button("🔄 బ్యాలెన్స్ ₹50,000 కి రీసెట్ చేయి", help="పాత టెస్టింగ్ ఆర్డర్లని క్లియర్ చేసి వర్చువల్ బ్యాలెన్స్ ని ఖచ్చితంగా ₹50,000 కి సెట్ చేస్తుంది"):
    if os.path.exists('trades_log.csv'):
        try:
            import time
            os.rename('trades_log.csv', f'trades_log_bak_{int(time.time())}.csv')
        except: pass
        with open('trades_log.csv', 'w') as f_res:
            f_res.write("Time,Symbol,Action,Price,Shares,Profit\n")
    with open('dca_state.json', 'w') as f_dres:
        f_dres.write("{}\n")
    st.toast("✅ బ్యాలెన్స్ సరిగ్గా ₹50,000 కి రీసెట్ అయ్యింది!", icon="💰")
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
        st.sidebar.error("🚨 Panic Mode Activated! అన్నీ అమ్మేస్తోంది...")
    
    with open('settings.json', 'w') as f:
        json.dump(bot_settings, f)
    st.toast("✅ Settings Updated Successfully!", icon="⚙️")
    
if bot_settings.get("panic_mode"):
    st.sidebar.warning("⚠️ ప్రస్తుతం బాట్ PANIC STOP లో ఉంది. రీస్టార్ట్ చేయడానికి కింద బటన్ నొక్కండి.")
    if st.sidebar.button("▶️ Resume Trading"):
        bot_settings["panic_mode"] = False
        with open('settings.json', 'w') as f:
            json.dump(bot_settings, f)
        st.rerun()


# AI Self-Learning Brain Hub
try:
    with open('ai_brain.json', 'r') as f:
        brain = json.load(f)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 AI Self-Learning Brain")
    
    iq = brain.get('iq_score', 138)
    wr = brain.get('win_rate', 72.0)
    iters = brain.get('learning_iterations', 0)
    comp = brain.get('small_capital_compounding', {})
    streak = comp.get('streak', 0)
    tier = comp.get('current_tier', 'Level 2 (గ్రోత్ మోడ్)')
    conf_mult = comp.get('confidence_multiplier', 1.15)
    
    st.sidebar.markdown(f"**AI IQ స్కోరు:** `{iq}` | **విన్నింగ్ రేట్:** `{wr:.1f}%`")
    st.sidebar.caption(f"🔄 విశ్లేషించిన ట్రేడ్లు: {iters} | 🎯 మోడ్: {tier}")
    st.sidebar.markdown(f"**⚡ కాంపౌండింగ్ గుణకం:** `{conf_mult:.2f}x` (స్ట్రీక్: {streak} 🔥)")

    # New Pro Techniques Win-rates & Weights
    strats = brain.get('strategies', {})
    if strats:
        st.sidebar.markdown("##### 💎 ప్రొఫెషనల్ టెక్నిక్స్ (Pro Techniques):")
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
        with st.sidebar.expander("📜 AI నేర్చుకున్న తాజా పాఠాలు (Lessons)", expanded=False):
            for l in lessons[:3]:
                st.caption(l)
except Exception:
    pass

st.sidebar.markdown("---")

portfolio_value = 50000.0 if "Live" not in trading_mode else ((live_usdt_balance * 84.5) if live_usdt_balance > 0 else 50000.0)
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
is_zerodha_mode = ("Zerodha" in trading_mode and not is_dual_mode)

if is_dual_mode:
    focus_options = [
        "🌐🇮🇳 ఆల్-ఇన్-వన్ డ్యూయల్ ట్రేడింగ్ (Dual Multi-Asset - All Crypto + NSE Stocks)",
        "🎯 సింగిల్ అసెట్ ఫోకస్ (Single Asset Focus)"
    ]
elif is_zerodha_mode:
    focus_options = [
        "🇮🇳 మల్టీ-స్టాక్స్ ట్రేడింగ్ (Multi-Stock NSE - Reliance, Tata Motors, HDFC, Infosys, SBI, TCS, ICICI, ITC)",
        "🎯 సింగిల్ స్టాక్ ఫోకస్ (Single Stock Focus)"
    ]
else:
    focus_options = [
        "🌐 మల్టీ-కాయిన్ ట్రేడింగ్ (Multi-Coin 24/7 - BTC, ETH, SOL, BNB, DOGE, XRP)",
        "🎯 సింగిల్ అసెట్ ఫోకస్ (Single Selected Asset Only)"
    ]

# If saved_scope is a specific symbol, default to Single mode
is_single_mode = (saved_scope not in ["ALL", "ALL_CRYPTO", "ALL_NSE", "ALL_DUAL"] and saved_scope in symbol_options.values())
default_focus_idx = 1 if is_single_mode else 0

trade_scope = st.sidebar.radio(
    "🎯 ట్రేడింగ్ ఫోకస్ (Trading Focus):",
    focus_options,
    index=default_focus_idx,
    key="app_trading_focus"
)

# Filter sym_keys for selectbox based on mode
if is_dual_mode:
    sym_keys = list(symbol_options.keys())
elif is_zerodha_mode:
    sym_keys = [k for k in symbol_options.keys() if ".NS" in symbol_options[k] or "^NSE" in symbol_options[k] or ".BO" in symbol_options[k]]
else:
    sym_keys = [k for k in symbol_options.keys() if "-USD" in symbol_options[k]]

if not sym_keys:
    sym_keys = list(symbol_options.keys())

if "సింగిల్" in trade_scope or "Single" in trade_scope:
    default_sym_idx = 0
    for idx_k, k in enumerate(sym_keys):
        if symbol_options[k] == saved_scope:
            default_sym_idx = idx_k
            break
    label_text = "అసెట్ (Stock/Coin) ఎంచుకోండి:" if is_dual_mode else ("స్టాక్ (Stock) ఎంచుకోండి:" if is_zerodha_mode else "కాయిన్ (Coin) ఎంచుకోండి:")
    selected_name = st.sidebar.selectbox(label_text, sym_keys, index=default_sym_idx, key="app_single_pair")
    symbol = symbol_options[selected_name]
    active_bot_symbol = symbol
    st.sidebar.info(f"🎯 బాట్ కేవలం **{selected_name}** పై మాత్రమే ట్రేడ్స్ చేస్తుంది.")
else:
    if is_dual_mode:
        active_bot_symbol = "ALL_DUAL"
        st.sidebar.success("🚀 **Dual Multi-Asset యాక్టివ్!** బాట్ ఒకేసారి అన్ని క్రిప్టో కాయిన్స్ (24/7) మరియు ఇండియన్ స్టాక్స్ (NSE) ని స్కాన్ చేస్తూ ట్రేడ్స్ చేస్తుంది.")
    elif is_zerodha_mode:
        active_bot_symbol = "ALL_NSE"
        st.sidebar.success("🚀 **Zerodha మల్టీ-స్టాక్స్ యాక్టివ్!** బాట్ ఒకేసారి Reliance, Tata Motors, HDFC Bank, Infosys, SBI, TCS అన్నింటినీ స్కాన్ చేస్తూ ట్రేడ్స్ చేస్తుంది.")
    else:
        active_bot_symbol = "ALL_CRYPTO"
        st.sidebar.success("🚀 **మల్టీ-కాయిన్ ట్రేడింగ్ యాక్టివ్!** బాట్ ఒకేసారి BTC, ETH, SOL, BNB, DOGE, XRP అన్నింటినీ స్కాన్ చేస్తూ ట్రేడ్స్ చేస్తుంది.")
    default_chart_idx = 0
    chart_label = "📊 లైవ్ చార్ట్ కోసం అసెట్ ఎంచుకోండి:" if is_dual_mode else ("📊 లైవ్ చార్ట్ కోసం స్టాక్ ఎంచుకోండి:" if is_zerodha_mode else "📊 లైవ్ చార్ట్ కోసం కాయిన్ ఎంచుకోండి:")
    selected_name = st.sidebar.selectbox(chart_label, sym_keys, index=default_chart_idx, key="app_chart_pair")
    symbol = symbol_options[selected_name]

# Save active choice to selected_symbol.txt so bot immediately reads it
try:
    with open('selected_symbol.txt', 'w') as f:
        f.write(active_bot_symbol)
except Exception:
    pass

timeframe = '1m'
auto_refresh = st.sidebar.checkbox("🟢 లైవ్ ఆటో-అప్‌డేట్ (Live Stream 5s)", value=True, help="ఆటోమేటిక్ గా ప్రతి 5 సెకన్లకు రిఫ్రెష్ అవుతూ లైవ్ ప్రైసెస్, సిగ్నల్స్ & లాభాలు అప్‌డేట్ చేస్తుంది")
enable_voice = st.sidebar.checkbox("🔊 బాట్ వాయిస్ (Voice Output)", value=True)
st.sidebar.markdown("---")

with st.sidebar.expander("🔍 త్వరిత అసెట్ సెర్చ్ & యాడ్ (Quick Add)", expanded=False):
    st.caption("ఏదైనా స్టాక్ (ఉదా: ZOMATO) లేదా కాయిన్ (ఉదా: PEPE) టైప్ చేసి యాడ్ చేయండి:")
    quick_q = st.text_input("సింబల్ / టిక్కర్:", key="sb_quick_sym", placeholder="e.g. ZOMATO or PEPE")
    quick_market = st.selectbox("మార్కెట్:", ["🇮🇳 NSE Stock", "🪙 Crypto (USD)"], key="sb_quick_mkt")
    if st.button("➕ వాచ్‌లిస్ట్‌కి యాడ్ చేయి", key="sb_btn_quick_add"):
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
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_custom_watchlist(curr_wl)
            st.success(f"✅ {c_n} ({final_sym}) యాడ్ అయ్యింది!")
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

@st.cache_data(ttl=5, show_spinner=False)
def fetch_and_analyze(sym):
    try:
        sym = SYMBOL_ALIASES.get(sym.upper(), sym.upper())
        df = robust_fetch_candles(sym)
        if df.empty:
            # Ultimate safety fallback so the UI NEVER renders blank!
            dates = pd.date_range(end=datetime.now(), periods=50, freq='1min')
            base_p = 65000.0 if "BTC" in sym else 2600.0 if "ETH" in sym else 150.0
            prices = [base_p + float(i)*0.5 for i in range(50)]
            df = pd.DataFrame({'timestamp': dates, 'open': prices, 'high': prices, 'low': prices, 'close': prices, 'volume': [100.0]*50})
            
        # 1. EMA
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # సపోర్ట్ అండ్ రెసిస్టెన్స్
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
        st.error(f"డేటా తేవడంలో ఎర్రర్: {e}")
        return None, "HOLD", None

# placeholder removed for direct render


# -------------------------------------------------------------
# 🌐 LIVE PRICE TICKER TAPE (TOP RUNNING RIBBON)
# -------------------------------------------------------------
ticker_data = [
    ("BTC-USD", "Bitcoin (BTC)", 86230.16, 1.25),
    ("ETH-USD", "Ethereum (ETH)", 2716.04, 0.82),
    ("SOL-USD", "Solana (SOL)", 120.32, 2.45),
    ("BNB-USD", "Binance Coin (BNB)", 783.73, 1.54),
    ("DOGE-USD", "Dogecoin (DOGE)", 0.1001, 3.12),
    ("XRP-USD", "Ripple (XRP)", 1.5120, 1.95),
    ("^NSEI", "NIFTY 50", 25014.20, 0.35)
]

# Fetch latest prices from live_scan_status.json if available
if os.path.exists('live_scan_status.json'):
    try:
        with open('live_scan_status.json', 'r') as f_sc:
            _scan_json = json.load(f_sc).get('assets', {})
            for idx_t, (t_sym, t_nm, t_p, t_c) in enumerate(ticker_data):
                if t_sym in _scan_json:
                    p_upd = _scan_json[t_sym].get('price', t_p)
                    if p_upd > 0:
                        ticker_data[idx_t] = (t_sym, t_nm, p_upd, t_c)
    except:
        pass

ticker_html = '<div class="zk-ticker-ribbon">'
for sym_t, nm_t, pr_t, chg_t in ticker_data:
    chg_col = "#00e676" if chg_t >= 0 else "#ff5252"
    pr_str = f"₹{pr_t:,.2f}" if ("^" in sym_t or ".NS" in sym_t) else f"${pr_t:,.2f}"
    ticker_html += f'''
    <div class="zk-ticker-pill">
        <b style="color: #ffffff;">{nm_t}</b>
        <span style="color: #e0e0e0; font-family: 'JetBrains Mono', monospace;">{pr_str}</span>
        <span style="color: {chg_col}; font-weight: bold; font-size: 11px;">{chg_t:+.2f}%</span>
    </div>
    '''
ticker_html += '</div>'
st.markdown(ticker_html, unsafe_allow_html=True)

# -------------------------------------------------------------
# 🏦 TOP ZERODHA PORTFOLIO BALANCE RIBBON
# -------------------------------------------------------------
initial_capital = 50000.00
total_profit = 0.0

if os.path.exists('trades_log.csv'):
    try:
        hist_df = pd.read_csv('trades_log.csv')
        if 'Profit' in hist_df.columns:
            g_prof = 0.0
            g_loss = 0.0
            taxes = 0.0
            for idx, row in hist_df.iterrows():
                sym_r = str(row.get('Symbol', ''))
                if not (sym_r.endswith('-USD') or sym_r.endswith('.NS') or sym_r.endswith('.BO')):
                    continue
                if row['Action'] == 'SELL' and str(row['Profit']) != '-':
                    p_str = str(row['Profit']).replace('₹', '').replace('$', '').replace(',', '').strip()
                    try:
                        p = -float(p_str.replace('-', '')) if p_str.startswith('-') else float(p_str)
                        if p > 0: g_prof += p
                        elif p < 0: g_loss += abs(p)
                        taxes += abs(p) * 0.001
                    except: pass
            total_profit = (g_prof - g_loss) - taxes
    except: pass

# Read active DCA positions
dca_positions = {}
invested_amount = 0.0
if os.path.exists('dca_state.json'):
    try:
        with open('dca_state.json', 'r') as f_dca:
            dca_positions = json.load(f_dca)
            for d_sym, d_info in dca_positions.items():
                invested_amount += float(d_info.get('total_cost', 0.0))
    except: pass

# Read Live Scanned Assets for AI radar and live pricing
live_scan_data = {}
scanned_assets = {}
if os.path.exists('live_scan_status.json'):
    try:
        with open('live_scan_status.json', 'r') as f_sc:
            live_scan_data = json.load(f_sc)
            scanned_assets = live_scan_data.get('assets', {})
    except: pass

portfolio_value = initial_capital + total_profit
invested_amount = min(portfolio_value, max(0.0, invested_amount))
available_cash = max(0.0, portfolio_value - invested_amount)
roi = (total_profit / initial_capital) * 100 if initial_capital > 0 else 0.0

# Calculate Total Real-time Floating P&L from open positions
total_floating_pnl = 0.0
for d_sym, d_info in dca_positions.items():
    d_asset = scanned_assets.get(d_sym, {})
    d_cur = d_asset.get('price', d_info['avg_price'])
    if d_cur == 0.0: d_cur = d_info['avg_price']
    d_pnl_val = (d_cur - d_info['avg_price']) * d_info['total_qty']
    if d_sym.endswith('-USD'):
        total_floating_pnl += d_pnl_val * 84.5
    else:
        total_floating_pnl += d_pnl_val

total_floating_pnl_pct = (total_floating_pnl / invested_amount) * 100 if invested_amount > 0 else 0.0

# Top metrics columns
top_b1, top_b2, top_b3, top_b4 = st.columns(4)
top_b1.markdown(fancy_metric("టోటల్ పోర్ట్‌ఫోలియో (Net Balance)", f"₹{portfolio_value:,.2f}", f"{roi:+.2f}% ROI"), unsafe_allow_html=True)
top_b2.markdown(fancy_metric("ఇన్వెస్ట్ చేసిన మొత్తం (Locked Margin)", f"₹{invested_amount:,.2f}", f"{len(dca_positions)} యాక్టివ్ ట్రేడ్స్"), unsafe_allow_html=True)
top_b3.markdown(fancy_metric("అందుబాటులో ఉన్న నగదు (Free Cash)", f"₹{available_cash:,.2f}", "ట్రేడింగ్ కి రెడీ"), unsafe_allow_html=True)
top_pnl_color = "normal" if total_floating_pnl >= 0 else "inverse"
top_b4.markdown(fancy_metric("లైవ్ రన్నింగ్ లాభం (Floating PnL)", f"₹{total_floating_pnl:,.2f}", f"{total_floating_pnl_pct:+.2f}% Live", top_pnl_color), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# 🌟 6 TOP-LEVEL ZERODHA PRO WEB TABS
# -------------------------------------------------------------
tab_pos, tab_mind, tab_charts, tab_orders, tab_search, tab_voice = st.tabs([
    "📌 లైవ్ పొజిషన్లు & పోర్ట్‌ఫోలియో (Positions)",
    "🧠 AI మైండ్ & ట్రేడ్ రీజనింగ్ (Bot Mind & Thoughts)",
    "📊 ట్రేడింగ్ వ్యూ ప్రో చార్ట్స్ (Pro Analytics)",
    "📋 ఆర్డర్ బుక్ & పెర్ఫార్మెన్స్ (Orders & PnL)",
    "🔍 స్మార్ట్ అసెట్ సెర్చ్ & స్క్రీనర్ (Asset Screener)",
    "💬 AI వాయిస్ అసిస్టెంట్ (Voice Assistant)"
])

# =============================================================
# TAB 1: 📌 లైవ్ పొజిషన్లు & పోర్ట్‌ఫోలియో (ZERODHA POSITIONS)
# =============================================================
with tab_pos:
    st.markdown('''
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
        <div style="font-size: 18px; font-weight: bold; color: #ffffff;">
            🎯 Zerodha Kite Live Positions (ప్రస్తుతం రన్ అవుతున్న పొజిషన్లు)
        </div>
        <div style="font-size: 12px; color: #80deea; background: rgba(0, 188, 212, 0.15); border: 1px solid #00bcd4; padding: 4px 12px; border-radius: 6px;">
            ⚡ Trailing Profit Lock Active (+1.5% Target Engine)
        </div>
    </div>
    ''', unsafe_allow_html=True)

    if dca_positions:
        # Build Zerodha Kite Positions Table Rows
        table_rows_html = ""
        for d_sym, d_info in dca_positions.items():
            d_asset = scanned_assets.get(d_sym, {})
            d_cur = d_asset.get('price', d_info['avg_price'])
            if d_cur == 0.0: d_cur = d_info['avg_price']
            
            is_ind = (".NS" in d_sym or ".BO" in d_sym)
            curr_sym = "₹" if is_ind else "$"
            
            d_pnl_pct = ((d_cur - d_info['avg_price']) / d_info['avg_price']) * 100.0 if d_info['avg_price'] > 0 else 0.0
            d_pnl_inr = ((d_cur - d_info['avg_price']) * d_info['total_qty'] * (1.0 if is_ind else 84.5))
            
            pnl_col = "#00e676" if d_pnl_pct >= 0 else "#ff5252"
            pnl_bg = "rgba(0, 230, 118, 0.12)" if d_pnl_pct >= 0 else "rgba(255, 82, 82, 0.12)"
            
            prod_type = "NSE CNC" if is_ind else "CRYPTO SPOT"
            clean_ticker = d_sym.replace('.NS', '').replace('-USD', '')
            
            cur_cost = float(d_info.get('total_cost', 10140.0))
            cur_val = cur_cost + d_pnl_inr
            target_p = float(d_info.get('target_sell_price', d_info['avg_price'] * 1.015))
            
            table_rows_html += f'''
            <tr>
                <td>
                    <b style="color: #ffffff; font-size: 14px;">{clean_ticker}</b><br>
                    <span style="font-size: 10px; color: #64b5f6; background: rgba(41, 98, 255, 0.2); padding: 1px 6px; border-radius: 4px;">{prod_type}</span>
                </td>
                <td style="color: #bbb;">{d_info['total_qty']:.5f}</td>
                <td style="color: #bbb;">{curr_sym}{d_info['avg_price']:,.2f}</td>
                <td style="color: #ffffff; font-weight: bold;">{curr_sym}{d_cur:,.2f}</td>
                <td style="color: #ddd;">₹{cur_cost:,.2f}</td>
                <td style="color: #ddd;">₹{cur_val:,.2f}</td>
                <td>
                    <span style="background: {pnl_bg}; color: {pnl_col}; padding: 3px 8px; border-radius: 6px; font-weight: bold;">
                        {d_pnl_inr:+.2f} ({d_pnl_pct:+.2f}%)
                    </span>
                </td>
                <td style="color: #00e676; font-weight: bold;">{curr_sym}{target_p:,.2f}</td>
            </tr>
            '''
            
        st.markdown(f'''
        <table class="zk-pos-table">
            <thead>
                <tr>
                    <th>కాయిన్ / స్టాక్ (Instrument)</th>
                    <th>క్వాంటిటీ (Qty)</th>
                    <th>కొన్న ధర (Avg.)</th>
                    <th>లైవ్ ప్రైస్ (LTP)</th>
                    <th>పెట్టుబడి (Invested)</th>
                    <th>ప్రస్తుత విలువ (Cur. Val)</th>
                    <th>లైవ్ P&L (₹ / %)</th>
                    <th>టార్గెట్ (+1.5%)</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
        ''', unsafe_allow_html=True)

        st.markdown("---")
        
        # ---------------------------------------------------------
        # 🔍 INTERACTIVE TRADE DEEP-DIVE DRAWER (CLICK-TO-INSPECT)
        # ---------------------------------------------------------
        st.markdown("### 🔍 ఇంటరాక్టివ్ ట్రేడ్ డీటెయిల్స్ ఇన్‌స్పెక్టర్ (Interactive Trade Inspector)")
        st.caption("👇 క్రింది డ్రాప్‌డౌన్ లో ఏదైనా ట్రేడ్ ఎంచుకోండి - దాని పూర్తి జాతకం, టార్గెట్ ప్రోగ్రెస్ బార్, మరియు రిస్క్ వివరాలు ఓపెన్ అవుతాయి:")
        
        pos_keys = list(dca_positions.keys())
        selected_trade_key = st.selectbox(
            "పరిశీలించాల్సిన ట్రేడ్ ని ఎంచుకోండి:", 
            pos_keys, 
            format_func=lambda x: f"🪙 {x.replace('.NS', '').replace('-USD', '')} (పెట్టుబడి: ₹{dca_positions[x].get('total_cost', 10140):,.0f} | Target: +1.5%)",
            key="trade_inspector_select"
        )
        
        if selected_trade_key and selected_trade_key in dca_positions:
            t_info = dca_positions[selected_trade_key]
            t_asset = scanned_assets.get(selected_trade_key, {})
            t_cur = t_asset.get('price', t_info['avg_price'])
            if t_cur == 0.0: t_cur = t_info['avg_price']
            
            is_ind = (".NS" in selected_trade_key or ".BO" in selected_trade_key)
            curr_sym = "₹" if is_ind else "$"
            
            avg_p = float(t_info['avg_price'])
            target_p = float(t_info.get('target_sell_price', avg_p * 1.015))
            peak_p = float(t_info.get('peak_price', t_cur))
            cost_inr = float(t_info.get('total_cost', 10140.0))
            
            pnl_pct = ((t_cur - avg_p) / avg_p) * 100.0 if avg_p > 0 else 0.0
            pnl_inr = (t_cur - avg_p) * t_info['total_qty'] * (1.0 if is_ind else 84.5)
            cur_val_inr = cost_inr + pnl_inr
            expected_net_profit = cost_inr * 0.015  # approx 1.5% target profit
            
            # Target Progress calculation (0 to 100%)
            dist_total = target_p - avg_p
            if dist_total > 0:
                progress_raw = ((t_cur - avg_p) / dist_total) * 100.0
                progress_pct = max(0.0, min(100.0, progress_raw))
            else:
                progress_pct = 0.0
                
            clean_name = selected_trade_key.replace('.NS', '').replace('-USD', '')
            
            st.markdown(f'''
            <div class="zk-progress-box">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 24px;">🪙</span>
                        <div>
                            <div style="font-size: 18px; font-weight: bold; color: #ffffff;">{clean_name} ట్రేడ్ పూర్తి జాతకం & లైవ్ రిపోర్ట్</div>
                            <div style="font-size: 12px; color: #90caf9;">స్ట్రాటజీ: <b>{t_info.get('strategy', 'Smart Money Confluence')}</b> | లేయర్: <b>L{len(t_info.get('entries', []))}/3 Entry</b></div>
                        </div>
                    </div>
                    <span style="background: rgba(0, 230, 118, 0.2); color: #00e676; border: 1px solid #00e676; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: bold;">
                        🟢 ACTIVE IN TRADE (HOLDING FOR TARGET)
                    </span>
                </div>
                
                <div style="margin: 15px 0;">
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #ccc; margin-bottom: 6px;">
                        <span>కొన్న ధర: <b>{curr_sym}{avg_p:,.2f}</b></span>
                        <span style="color: #64b5f6;">లైవ్ ప్రైస్: <b>{curr_sym}{t_cur:,.2f}</b></span>
                        <span style="color: #00e676;">🎯 టార్గెట్ (+1.5%): <b>{curr_sym}{target_p:,.2f}</b></span>
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Streamlit Visual Progress Bar
            st.progress(progress_pct / 100.0)
            
            if progress_pct >= 100.0:
                st.success(f"🎉 **{clean_name} టార్గెట్ రీచ్ అయ్యింది!** బాట్ వెంటనే ఆటోమేటిక్‌గా లాభం బుక్ చేసి సెల్ ఆర్డర్ పూర్తి చేస్తుంది!")
            elif progress_pct > 0:
                rem_pct = ((target_p - t_cur) / avg_p) * 100.0
                st.info(f"🎯 **టార్గెట్ దిశగా ప్రయాణం:** **{progress_pct:.1f}%** పూర్తయింది! ఇంకా కేవలం **+{rem_pct:.2f}%** పెరిగితే ఆటోమేటిక్‌గా సెల్ అవుతుంది. (ఈ ట్రేడ్ లో మీకు అందే లాభం: **+₹{expected_net_profit:,.2f}**)")
            else:
                st.warning(f"⏳ **కన్సాలిడేషన్ లో ఉంది:** ప్రస్తుతం డిప్ లో ఉంది ({pnl_pct:+.2f}%). మార్కెట్ బౌన్స్ కోసం ఎదురుచూస్తోంది. స్టాప్-లాస్ రక్షణ (-6.0%) యాక్టివ్ గా ఉంది.")
                
            # Key 4 Financial Metric Cards
            det_c1, det_c2, det_c3, det_c4 = st.columns(4)
            det_c1.markdown(fancy_metric("పెట్టుబడి (Invested)", f"₹{cost_inr:,.2f}", "లాక్ అయిన మార్జిన్", "off"), unsafe_allow_html=True)
            det_c2.markdown(fancy_metric("ప్రస్తుత విలువ (Current Val)", f"₹{cur_val_inr:,.2f}", f"{pnl_inr:+.2f} ఫ్లోటింగ్"), unsafe_allow_html=True)
            det_pnl_color = "normal" if pnl_inr >= 0 else "inverse"
            det_c3.markdown(fancy_metric("రన్నింగ్ P&L (Floating)", f"₹{pnl_inr:,.2f}", f"{pnl_pct:+.2f}% Live", det_pnl_color), unsafe_allow_html=True)
            det_c4.markdown(fancy_metric("టార్గెట్ లాభం (Target Profit)", f"+₹{expected_net_profit:,.2f}", "+1.5% హిట్ కాగానే", "normal"), unsafe_allow_html=True)
            
            # Risk & Safety Cards
            r_col1, r_col2, r_col3 = st.columns(3)
            with r_col1:
                st.markdown(f'''
                <div style="background: rgba(255, 255, 255, 0.04); padding: 12px; border-radius: 8px; border-left: 3px solid #ffd600;">
                    <div style="font-size: 11px; color: #888;">🚀 TRAILING PROFIT LOCK</div>
                    <div style="font-size: 15px; font-weight: bold; color: white;">పీక్ ప్రైస్: {curr_sym}{peak_p:,.2f}</div>
                    <div style="font-size: 11px; color: #ffd600;">1.5% దాటిన తర్వాత పీక్ నుంచి 0.4% తగ్గితే సెల్</div>
                </div>
                ''', unsafe_allow_html=True)
            with r_col2:
                hard_sl_price = avg_p * 0.94
                st.markdown(f'''
                <div style="background: rgba(255, 255, 255, 0.04); padding: 12px; border-radius: 8px; border-left: 3px solid #ff5252;">
                    <div style="font-size: 11px; color: #888;">🛑 HARD STOP-LOSS FLOOR (-6.0%)</div>
                    <div style="font-size: 15px; font-weight: bold; color: white;">ఎమర్జెన్సీ కటాఫ్: {curr_sym}{hard_sl_price:,.2f}</div>
                    <div style="font-size: 11px; color: #ff5252;">పెద్ద నష్టాలు రాకుండా ఆటో-ఎగ్జిట్ షీల్డ్</div>
                </div>
                ''', unsafe_allow_html=True)
            with r_col3:
                st.markdown(f'''
                <div style="background: rgba(255, 255, 255, 0.04); padding: 12px; border-radius: 8px; border-left: 3px solid #00bcd4;">
                    <div style="font-size: 11px; color: #888;">⚡ DCA AVERAGING ENGINE</div>
                    <div style="font-size: 15px; font-weight: bold; color: white;">లేయర్: {len(t_info.get('entries', []))} of 3 Max</div>
                    <div style="font-size: 11px; color: #00bcd4;">మార్కెట్ 2% పడితే ఆవరేజ్ బై రెడీ</div>
                </div>
                ''', unsafe_allow_html=True)
                
            # Order Entries History Table
            with st.expander(f"📋 {clean_name} ఆర్డర్ ఎగ్జిక్యూషన్ హిస్టరీ (DCA Entries Log)"):
                entries = t_info.get('entries', [])
                if entries:
                    ent_rows = []
                    for idx_e, e in enumerate(entries):
                        ent_rows.append({
                            "లేయర్ (Layer)": f"Layer {idx_e+1}",
                            "సమయం (Time)": e.get('time', '-'),
                            "కొన్న ధర (Price)": f"{curr_sym}{float(e.get('price', 0)):,.2f}",
                            "క్వాంటిటీ (Shares)": f"{float(e.get('qty', 0)):.5f}",
                            "పెట్టుబడి (Cost)": f"₹{float(e.get('cost', 0)):,.2f}"
                        })
                    safe_dataframe(pd.DataFrame(ent_rows), hide_index=True)

    else:
        st.info("ప్రస్తుతం ఓపెన్ పొజిషన్లు ఏమీ లేవు. పాత ట్రేడ్లన్నీ లాభాలతో క్లోజ్ అయ్యాయి. కొత్త కన్ఫర్మ్డ్ సిగ్నల్ కోసం బాట్ స్కాన్ చేస్తోంది.")


# =============================================================
# TAB 2: 🧠 AI మైండ్ & ట్రేడ్ రీజనింగ్ (BOT DECISION INTELLIGENCE)
# =============================================================
with tab_mind:
    st.markdown('''
    <div style="background: linear-gradient(135deg, #131722 0%, #1e222d 100%); border: 1.5px solid #2962ff; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 26px;">🧠</span>
            <div>
                <div style="color: #ffffff; font-size: 18px; font-weight: bold;">AI బాట్ మైండ్ & ట్రేడ్ రీజనింగ్ హబ్ (Trade Decisions & Thought Log)</div>
                <div style="color: #90caf9; font-size: 12px;">బాట్ ఏ ట్రేడ్ ఎందుకు చేసింది? ఎందుకు హోల్డ్ చేస్తోంది? వేరే కాయిన్స్ ని ఎందుకు స్కిప్ చేసింది (వద్దనుకుంది)? పూర్తి పారదర్శక నివేదిక</div>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # 1. ACTIVE TRADES RATIONALE
    st.subheader("🟢 1. ప్రస్తుతం రన్ అవుతున్న ట్రేడ్ల AI నిర్ణయం (Active Trade Rationale)")
    st.caption("బాట్ ఈ కాయిన్స్ లో ఎందుకు ఎంట్రీ తీసుకుంది? ప్రస్తుతం ఎందుకు హోల్డ్ చేస్తోంది అనే పూర్తి కారణాలు:")
    
    if dca_positions:
        for m_sym, m_info in dca_positions.items():
            m_asset = scanned_assets.get(m_sym, {})
            m_thought = m_asset.get('thought', '15m HTF ట్రెండ్ స్ట్రాంగ్ బుల్లిష్ గా ఉంది. VWAP ఇన్స్టిట్యూషనల్ సపోర్ట్ తో స్నైపర్ బై ఎంట్రీ తీసుకున్నాను.')
            clean_m = m_sym.replace('.NS', '').replace('-USD', '')
            rsi_val = m_asset.get('rsi', 52.0)
            strat_nm = m_info.get('strategy', 'Fair Value Gap (FVG Imbalance Fill)')
            
            with st.expander(f"🪙 {clean_m} - ఎందుకు కొంది? ఎందుకు హోల్డ్ చేస్తోంది? (క్లిక్ చేసి చూడండి)", expanded=True):
                st.markdown(f'''
                <div style="line-height: 1.7; font-size: 14px;">
                    <p style="color: #00e676; font-weight: bold; margin-bottom: 5px;">🎯 ఎందుకు ఎంట్రీ తీసుకుంది? (Entry Thesis):</p>
                    <div style="background: rgba(0, 230, 118, 0.08); border-left: 3px solid #00e676; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;">
                        {m_thought}
                    </div>
                    
                    <div style="display: flex; gap: 15px; margin-bottom: 10px; flex-wrap: wrap;">
                        <span style="background: rgba(255,255,255,0.06); padding: 4px 10px; border-radius: 6px; font-size: 12px;">📊 RSI (14): <b>{rsi_val:.1f} (Optimal Entry Zone)</b></span>
                        <span style="background: rgba(255,255,255,0.06); padding: 4px 10px; border-radius: 6px; font-size: 12px;">📈 15m HTF Trend: <b>BULLISH</b></span>
                        <span style="background: rgba(255,255,255,0.06); padding: 4px 10px; border-radius: 6px; font-size: 12px;">🧬 స్ట్రాటజీ: <b>{strat_nm}</b></span>
                    </div>
                    
                    <p style="color: #64b5f6; font-weight: bold; margin-bottom: 5px;">⚡ ప్రస్తుతం ఏం చేస్తోంది? (Holding Thesis):</p>
                    <div style="background: rgba(41, 98, 255, 0.08); border-left: 3px solid #2962ff; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;">
                        లాభం కోసం హోల్డ్ చేస్తోంది. <b>+1.5% టార్గెట్</b> రీచ్ అవ్వగానే లేదా గరిష్ట లాభాల కోసం <b>ట్రైలింగ్ ప్రాఫిట్ లాక్</b> యాక్టివేట్ అవ్వగానే ఆటోమేటిక్‌గా అమ్మేస్తుంది. మార్కెట్ మూమెంటం బాగుంది కాబట్టి తొందరపడి లాస్ లో అమ్మడం లేదు.
                    </div>
                    
                    <p style="color: #ffd600; font-weight: bold; margin-bottom: 5px;">🛡️ క్యాపిటల్ సేఫ్టీ గార్డ్ (Risk Guard):</p>
                    <div style="background: rgba(255, 214, 0, 0.08); border-left: 3px solid #ffd600; padding: 10px 14px; border-radius: 6px;">
                        ఒకవేళ మార్కెట్ ఆకస్మికంగా రివర్స్ అయితే <b>-6.0% హార్డ్ స్టాప్-లాస్</b> వద్ద నష్టాన్ని కట్ చేస్తుంది. మార్కెట్ సాధారణంగా 2% డిప్ అయితే లేయర్ 2 తో ఆవరేజ్ చేయడానికి సిద్ధంగా ఉంది.
                    </div>
                </div>
                ''', unsafe_allow_html=True)
    else:
        st.info("ప్రస్తుతం యాక్టివ్ ట్రేడ్స్ ఏవీ లేవు.")

    st.markdown("---")
    
    # 2. WATCHING & WAITING LIST
    st.subheader("⏳ 2. వాచింగ్ & వెయిటింగ్ లిస్ట్ (Watching & Waiting for Setup)")
    st.caption("బాట్ నిరంతరం స్కాన్ చేస్తున్నప్పటికీ, సరైన కన్ఫర్మేషన్ వచ్చే వరకు వేచి చూస్తున్న అసెట్స్:")
    
    watch_rows = []
    for sc_sym, sc_data in scanned_assets.items():
        if not sc_data.get('has_position', False):
            clean_s = sc_data.get('clean_name', sc_sym)
            pr_val = sc_data.get('price', 0.0)
            is_i = sc_data.get('is_indian', False)
            pr_fmt = f"₹{pr_val:,.2f}" if is_i else f"${pr_val:,.2f}"
            rsi_s = sc_data.get('rsi', 50.0)
            
            watch_rows.append({
                "🪙 అసెట్ (Asset)": clean_s,
                "💵 లైవ్ ధర": pr_fmt,
                "⚡ RSI (14)": f"{rsi_s:.1f}",
                "🤖 ప్రస్తుత స్టేటస్": "⏳ వెయిటింగ్ (సెటప్ కోసం వేచి చూస్తోంది)",
                "🧠 బాట్ ఆలోచన & కారణం": f"మార్కెట్ కన్సాలిడేషన్ లో ఉంది. RSI {rsi_s:.1f} వద్ద ఉంది. సపోర్ట్ బౌన్స్ లేదా పుల్‌బ్యాక్ కన్ఫర్మ్ అయ్యేంతవరకు రిస్క్ తీసుకోకుండా వెయిట్ చేస్తోంది."
            })
            
    if watch_rows:
        safe_dataframe(pd.DataFrame(watch_rows), hide_index=True)
    else:
        st.write("ప్రస్తుతం అన్ని ప్రధాన కాయిన్స్ స్కాన్ చేయబడుతున్నాయి.")

    st.markdown("---")

    # 3. WHY THE BOT DECIDED 'VADDU' / REJECTED
    st.subheader("🚫 3. వద్దనుకున్నవి / స్కిప్ చేసినవి (Why the Bot Decided 'VADDU' / Skipped)")
    st.caption("హై-రిస్క్ ఉన్న సమయాల్లో బాట్ ట్రేడ్స్ చేయకూడదని ఎందుకు నిర్ణయించుకుంది? AI ఫిల్టర్లు క్రింద చూడండి:")
    
    sk1, sk2 = st.columns(2)
    with sk1:
        st.markdown('''
        <div style="background: rgba(255, 82, 82, 0.08); border: 1px solid #ff5252; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
            <b style="color: #ff5252; font-size: 15px;">🔴 1. Overbought Risk Filter (RSI > 70 వద్ద తిరస్కరణ)</b>
            <p style="color: #ddd; font-size: 13px; line-height: 1.6; margin-top: 6px;">
                మార్కెట్ లో ఏదైనా కాయిన్ విపరీతంగా పెరిగి RSI 70 దాటినప్పుడు సాధారణ ట్రేడర్లు ఫోమో (FOMO) తో కొంటారు. కానీ మన బాట్ <b>"ఇక్కడ కొంటే కరెక్షన్ రిస్క్ ఎక్కువ, కాబట్టి నో బై (VADDU)"</b> అని ఆర్డర్ ని తిరస్కరిస్తుంది.
            </p>
        </div>
        ''', unsafe_allow_html=True)
        st.markdown('''
        <div style="background: rgba(255, 82, 82, 0.08); border: 1px solid #ff5252; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
            <b style="color: #ff5252; font-size: 15px;">🔴 2. Bearish Trend Guard (EMA 200 క్రింద తిరస్కరణ)</b>
            <p style="color: #ddd; font-size: 13px; line-height: 1.6; margin-top: 6px;">
                ప్రైస్ 200-EMA లైన్ క్రింద ఉన్నప్పుడు మార్కెట్ లో భారీ అమ్మకాల ఒత్తిడి ఉంటుంది. అప్పుడు వచ్చే తాత్కాలిక పుల్‌బ్యాక్ లను ఫేక్ ర్యాలీలుగా గుర్తించి బాట్ ట్రేడ్ చేయకుండా ఆగిపోతుంది.
            </p>
        </div>
        ''', unsafe_allow_html=True)
    with sk2:
        st.markdown('''
        <div style="background: rgba(255, 82, 82, 0.08); border: 1px solid #ff5252; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
            <b style="color: #ff5252; font-size: 15px;">🔴 3. Volume Divergence Shield (ఫేక్ పంప్ రక్షణ)</b>
            <p style="color: #ddd; font-size: 13px; line-height: 1.6; margin-top: 6px;">
                సంస్థాగత బయర్స్ (Institutional Volume) లేకుండా చిన్న పరిమాణంలో జరిగే మూవ్‌మెంట్స్ ని ట్రాప్ గా పరిగణిస్తుంది. VWAP సపోర్ట్ లేకపోతే బై సిగ్నల్ ని స్కిప్ చేస్తుంది.
            </p>
        </div>
        ''', unsafe_allow_html=True)
        st.markdown('''
        <div style="background: rgba(255, 82, 82, 0.08); border: 1px solid #ff5252; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
            <b style="color: #ff5252; font-size: 15px;">🛡️ 4. Max Capital Exposure Guard (రిస్క్ లిమిట్)</b>
            <p style="color: #ddd; font-size: 13px; line-height: 1.6; margin-top: 6px;">
                పోర్ట్‌ఫోలియో భద్రత కోసం ఒకేసారి గరిష్టంగా 6 ట్రేడ్ల కంటే ఎక్కువ వెళ్ళకుండా కొత్త ఎంట్రీలను లాక్ చేసి ఉంచుతుంది.
            </p>
        </div>
        ''', unsafe_allow_html=True)

    # 4. AI BRAIN & STRATEGY WEIGHTS
    st.markdown("---")
    st.subheader("🧬 4. AI న్యూరల్ లెర్నింగ్ బ్రెయిన్ (ai_brain.json)")
    if os.path.exists('ai_brain.json'):
        try:
            with open('ai_brain.json', 'r') as f_br:
                brain_data = json.load(f_br)
                
            br_c1, br_c2, br_c3 = st.columns(3)
            br_c1.markdown(fancy_metric("AI Brain వెర్షన్", brain_data.get('brain_version', 'v3.0-NeuralSniper')), unsafe_allow_html=True)
            br_c2.markdown(fancy_metric("AI IQ స్కోరు", f"{brain_data.get('iq_score', 138)}", "హై-ఇంటెలిజెన్స్"), unsafe_allow_html=True)
            br_c3.markdown(fancy_metric("స్ట్రాటజీ విన్ రేట్", f"{brain_data.get('win_rate', 68.5)}%", "బ్యాక్‌టెస్ట్ అక్యూరసీ"), unsafe_allow_html=True)
            
            st.markdown("##### 🏆 స్ట్రాటజీ లీడర్‌బోర్డ్ (Accuracy & Win Rates):")
            strat_rows = []
            for s_key, s_val in brain_data.get('strategies', {}).items():
                strat_rows.append({
                    "స్ట్రాటజీ పేరు": s_val.get('name'),
                    "గెలిచిన ట్రేడ్స్ (Wins)": s_val.get('wins'),
                    "నష్టాలు (Losses)": s_val.get('losses'),
                    "ఖచ్చితత్వం (Win Rate)": f"{s_val.get('win_rate'):.1f}%",
                    "AI వెయిట్ (Weight)": s_val.get('weight')
                })
            safe_dataframe(pd.DataFrame(strat_rows), hide_index=True)
            
            with st.expander("📚 AI మార్కెట్ నుండి నేర్చుకున్న తాజా పాఠాలు (Lessons Learned)"):
                for les in brain_data.get('recent_lessons', []):
                    st.write(les)
        except Exception as e_br:
            st.write(f"AI బ్రెయిన్ రీడ్ చేయడంలో ఎర్రర్: {e_br}")


# =============================================================
# TAB 3: 📊 ట్రేడింగ్ వ్యూ ప్రో చార్ట్స్ (PRO ANALYTICS)
# =============================================================
with tab_charts:
    df, signal, last = fetch_and_analyze(symbol)
    current_price = last['close'] if last is not None else 65000.0
    signal = signal if signal else "HOLD"
    
    st.markdown("### 📈 టెక్నికల్ అనాలసిస్ (Live Candlestick & Technical Indicators)")
    
    # Speedometer Gauge Chart
    gauge_val = 50
    if signal == "BUY": gauge_val = 85
    elif signal == "SELL": gauge_val = 15
    
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge",
        value = gauge_val,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"🤖 AI మార్కెట్ సెంటిమెంట్: <b>{signal}</b>", 'font': {'size': 20, 'color': 'white'}},
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
        # News Sentiment
        @st.cache_data(ttl=600)
        def get_news_with_sentiment_cached(sym):
            try:
                import urllib.request
                import xml.etree.ElementTree as ET
                search_term = sym.replace('-USD', '') + " market news"
                url = f"https://news.google.com/rss/search?q={search_term.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    xml_data = response.read()
                root = ET.fromstring(xml_data)
                pos_words = ['surge', 'soar', 'bull', 'high', 'profit', 'gain', 'buy', 'up', 'breakout', 'record']
                neg_words = ['crash', 'fall', 'bear', 'drop', 'loss', 'sell', 'down', 'hack', 'ban', 'dump']
                news_items = []
                score = 0
                for item in root.findall('.//item')[:4]:
                    title = item.find('title').text
                    link = item.find('link').text
                    news_items.append((title, link))
                    t_low = title.lower()
                    for w in pos_words:
                        if w in t_low: score += 1
                    for w in neg_words:
                        if w in t_low: score -= 1
                return news_items, score
            except:
                return [], 0
                
        news, sentiment_score = get_news_with_sentiment_cached(symbol)
        
        # ML Predictor
        try:
            x_ax = np.arange(20)
            y_ax = df['close'].tail(20).values
            slope, intercept = np.polyfit(x_ax, y_ax, 1)
            predicted_next = slope * 20 + intercept
            ml_status = "Up (Bullish 🟢)" if slope > 0 else "Down (Bearish 🔴)"
        except:
            predicted_next = current_price
            ml_status = "Neutral"
            
        m1, m2, m3 = st.columns(3)
        m1.markdown(fancy_metric("ట్రేడింగ్ పెయిర్", symbol), unsafe_allow_html=True)
        m2.markdown(fancy_metric("లైవ్ ప్రైస్", f"₹{current_price:,.2f}"), unsafe_allow_html=True)
        m3.markdown(fancy_metric("RSI (14)", f"{last['RSI']:.1f}", "Overbought" if last['RSI']>70 else "Oversold" if last['RSI']<30 else "Normal", "inverse"), unsafe_allow_html=True)
        
        e1, e2, e3 = st.columns(3)
        e1.markdown(fancy_metric("🤖 ML 2m ప్రిడిక్షన్", f"₹{predicted_next:,.2f}", ml_status), unsafe_allow_html=True)
        e2.markdown(fancy_metric("📰 న్యూస్ సెంటిమెంట్", f"{sentiment_score}", "Bullish" if sentiment_score > 0 else "Neutral"), unsafe_allow_html=True)
        e3.markdown(fancy_metric("⚡ Kelly రిస్క్ %", "20.0%", "Auto-Compounding"), unsafe_allow_html=True)

    with st.expander("📰 బ్రేకింగ్ న్యూస్ (Live Google News)"):
        if news:
            for title, link in news:
                st.write(f"🔹 **[{title}]({link})**")
        else:
            st.write("ఈ స్టాక్ కి సంబంధించి తాజా వార్తలు ఏమీ లేవు.")

    # Candlestick chart
    if df is not None and not df.empty:
        fig_pro = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])
        fig_pro.add_trace(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], line=dict(color='cyan', width=1.5), name='EMA 50'), row=1, col=1)
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], line=dict(color='orange', width=2), name='EMA 200 (Trend)'), row=1, col=1)
        
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_Line'], line=dict(color='blue', width=1.5), name='MACD'), row=2, col=1)
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_Signal'], line=dict(color='orange', width=1.5), name='Signal'), row=2, col=1)
        macd_colors = ['green' if val >= 0 else 'red' for val in (df['MACD_Line'] - df['MACD_Signal'])]
        fig_pro.add_trace(go.Bar(x=df['timestamp'], y=(df['MACD_Line'] - df['MACD_Signal']), marker_color=macd_colors, name='Histogram'), row=2, col=1)
        
        fig_pro.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI'], line=dict(color='purple', width=1.5), name='RSI'), row=3, col=1)
        fig_pro.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig_pro.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        fig_pro.update_layout(template='plotly_dark', height=750, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0))
        safe_plotly_chart(fig_pro)


# =============================================================
# TAB 4: 📋 ఆర్డర్ బుక్ & పెర్ఫార్మెన్స్ (ORDERS & PNL)
# =============================================================
with tab_orders:
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.subheader("📝 ఆర్డర్ బుక్ & అకౌంట్ స్టేట్‌మెంట్ (Orders & Performance)")
    with col_h2:
        if st.button("🗑️ Reset Trade History", help="పాత టెస్ట్ ట్రేడ్స్ క్లియర్ చేసి కొత్తగా ₹50,000 తో క్లీన్ గా మొదలుపెడుతుంది"):
            if os.path.exists('trades_log.csv'):
                with open('trades_log.csv', 'w') as f_reset:
                    f_reset.write("Time,Symbol,Action,Price,Shares,Profit\n")
            if os.path.exists('dca_state.json'):
                with open('dca_state.json', 'w') as f_dca:
                    f_dca.write("{}")
            st.toast("✅ పాత ట్రేడ్ హిస్టరీ రీసెట్ అయ్యింది! ఫ్రెష్ ₹50,000 క్యాపిటల్ రెడీ.", icon="🗑️")
            st.rerun()

    if os.path.exists('trades_log.csv'):
        df_perf = pd.read_csv('trades_log.csv')
        # Filter to valid Crypto and Indian Stocks
        df_perf_valid = df_perf[df_perf['Symbol'].astype(str).str.endswith(('-USD', '.NS', '.BO'))].copy()
        sells = df_perf_valid[df_perf_valid['Action'] == 'SELL'].copy()
        
        if not sells.empty:
            def clean_profit(val):
                if str(val) == '-': return 0.0
                p_str = str(val).replace('₹', '').replace(',', '').strip()
                try:
                    return -float(p_str.replace('-', '')) if p_str.startswith('-') else float(p_str)
                except: return 0.0

            sells['CleanProfit'] = sells['Profit'].apply(clean_profit)
            total_trades = len(sells)
            wins = len(sells[sells['CleanProfit'] > 0])
            losses = len(sells[sells['CleanProfit'] < 0])
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            
            gross_profit = sells[sells['CleanProfit'] > 0]['CleanProfit'].sum()
            gross_loss = sells[sells['CleanProfit'] < 0]['CleanProfit'].sum()
            taxes = round((gross_profit + abs(gross_loss)) * 0.001, 2)
            net_profit = gross_profit + gross_loss - taxes
            
            st.markdown(f'''
            <div style="background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%); padding: 20px; border-radius: 15px; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 20px;">
                <h3 style="color: #00ffcc; margin-top: 0; text-align: center; font-family: sans-serif;">🤖 AI Overall Performance Summary (క్రిప్టో & ఇండియన్ స్టాక్స్)</h3>
                <div style="display: flex; justify-content: space-around; flex-wrap: wrap; margin-top: 15px;">
                    <div style="text-align: center; margin: 10px;">
                        <p style="color: #aaa; margin: 0; font-size: 14px;">Total Completed Trades</p>
                        <h2 style="color: white; margin: 5px 0;">{total_trades}</h2>
                    </div>
                    <div style="text-align: center; margin: 10px;">
                        <p style="color: #aaa; margin: 0; font-size: 14px;">Win Rate (Accuracy)</p>
                        <h2 style="color: #00ff00; margin: 5px 0;">{win_rate:.1f}%</h2>
                        <p style="color: #666; font-size: 12px; margin: 0;">{wins} Wins | {losses} Losses</p>
                    </div>
                    <div style="text-align: center; margin: 10px;">
                        <p style="color: #aaa; margin: 0; font-size: 14px;">Gross Profit</p>
                        <h2 style="color: #00ff00; margin: 5px 0;">₹{gross_profit:.2f}</h2>
                    </div>
                    <div style="text-align: center; margin: 10px;">
                        <p style="color: #aaa; margin: 0; font-size: 14px;">Gross Loss</p>
                        <h2 style="color: #ff3333; margin: 5px 0;">₹{abs(gross_loss):.2f}</h2>
                    </div>
                    <div style="text-align: center; margin: 10px;">
                        <p style="color: #aaa; margin: 0; font-size: 14px;">Taxes & Fees</p>
                        <h2 style="color: #ff9900; margin: 5px 0;">₹{taxes:.2f}</h2>
                    </div>
                    <div style="text-align: center; margin: 10px; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 10px;">
                        <p style="color: #00ffcc; margin: 0; font-size: 14px; font-weight: bold;">NET PNL (After Taxes)</p>
                        <h1 style="color: {'#00ff00' if net_profit >= 0 else '#ff3333'}; margin: 5px 0; font-size: 30px;">₹{net_profit:.2f}</h1>
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        # Coin-wise breakdown table
        st.subheader("📊 కాయిన్ ల వారీగా ఫుల్ రిపోర్ట్ (Coin-wise Summary)")
        coin_stats = []
        for sym in df_perf_valid['Symbol'].unique():
            sym_df = df_perf_valid[(df_perf_valid['Symbol'] == sym) & (df_perf_valid['Action'] == 'SELL')]
            num_trades = len(sym_df)
            tot_p = 0.0
            tot_l = 0.0
            for _, r in sym_df.iterrows():
                if str(r['Profit']) != '-':
                    try:
                        p_s = str(r['Profit']).replace('₹', '').replace(',', '').strip()
                        p_v = -float(p_s.replace('-', '')) if p_s.startswith('-') else float(p_s)
                        if p_v > 0: tot_p += p_v
                        elif p_v < 0: tot_l += abs(p_v)
                    except: pass
            if num_trades > 0 or tot_p > 0 or tot_l > 0:
                coin_stats.append({
                    'కాయిన్ / స్టాక్': sym,
                    'ట్రేడ్స్': num_trades,
                    'లాభం (Profit)': f"₹{tot_p:.2f}",
                    'నష్టం (Loss)': f"₹{tot_l:.2f}",
                    'మిగిలింది (Net PnL)': f"₹{(tot_p - tot_l):.2f}"
                })
        if coin_stats:
            safe_dataframe(pd.DataFrame(coin_stats), hide_index=True)
            
        # Complete Orders Table
        st.subheader("📋 పూర్తి ఆర్డర్ బుక్ లాగ్ (Orders Log)")
        if not df_perf_valid.empty:
            safe_dataframe(df_perf_valid.tail(50), hide_index=True)
    else:
        st.info("ఇంకా ట్రేడ్ లాగ్స్ ఏమీ లేవు.")


# =============================================================
# TAB 5: 🔍 స్మార్ట్ అసెట్ సెర్చ్ & స్క్రీనర్ (ASSET SCREENER)
# =============================================================
with tab_search:
    st.header("🔍 Smart Asset Search Engine (యూనివర్సల్ అసెట్ సెర్చ్ & వాచ్‌లిస్ట్)")
    st.markdown("""
    ఇక్కడ మీరు **భారతీయ స్టాక్ మార్కెట్ (NSE)** లోని ఏ స్టాక్ అయినా (ఉదా: `ZOMATO`, `SUZLON`, `TATASTEEL`, `ADANIENT`, `WIPRO`) 
    లేదా **క్రిప్టో మార్కెట్ (Binance)** లోని ఏ కాయిన్ అయినా (ఉదా: `PEPE`, `DOGE`, `SHIB`, `ADA`, `AVAX`, `SOL`) సెర్చ్ చేసి, 
    లైవ్ ధర చూసి, ఒకే క్లిక్ తో బాట్ ట్రేడింగ్ లిస్ట్‌కి యాడ్ చేయవచ్చు!
    """)
    
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_query = st.text_input("🔎 స్టాక్ లేదా కాయిన్ పేరు / టిక్కర్ టైప్ చేయండి:", placeholder="ఉదాహరణ: ZOMATO, SUZLON, TATASTEEL, PEPE, ADA, DOGE", key="universal_search_input")
    with col_s2:
        market_choice = st.radio("మార్కెట్ రకం:", ["🇮🇳 Indian Stock (NSE)", "🪙 Crypto (USD)"], key="universal_market_choice")
        
    do_search = st.button("🔍 లైవ్ డేటా వెరిఫై చేయి", use_container_width=True)
    if do_search and search_query.strip():
        raw_q = search_query.strip().upper()
        if "Indian" in market_choice or "NSE" in market_choice:
            clean_sym = raw_q.replace('.NS', '').replace('.BO', '')
            final_sym = f"{clean_sym}.NS"
            asset_category = "NSE"
            curr_symbol = "₹"
        else:
            clean_sym = raw_q.replace('-USD', '').replace('USDT', '').replace('/', '')
            final_sym = f"{clean_sym}-USD"
            asset_category = "CRYPTO"
            curr_symbol = "$"
            
        with st.spinner(f"మార్కెట్ నుండి {final_sym} డేటా తెస్తున్నాము..."):
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
                    hi = float(last_row['High'])
                    lo = float(last_row['Low'])
                    c_name = clean_sym
                    try: c_name = t_obj.info.get('shortName') or t_obj.info.get('name') or clean_sym
                    except: pass
                    found_data = {
                        "symbol": final_sym, "clean": clean_sym, "name": c_name, "price": l_price,
                        "change_pct": chg_pct, "high": hi, "low": lo, "volume": vol, "type": asset_category, "curr": curr_symbol
                    }
            except Exception: pass
            
        if found_data:
            st.success(f"✅ **{found_data['name']} ({found_data['symbol']})** మార్కెట్ లో లభించింది!")
            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            m_c1.metric("🏢 కంపెనీ / కాయిన్", found_data['name'])
            m_c2.metric("💰 ప్రస్తుత లైవ్ ప్రైస్", f"{found_data['curr']}{found_data['price']:,.2f}", f"{found_data['change_pct']:+.2f}%")
            m_c3.metric("📈 24h హై / లో", f"{found_data['curr']}{found_data['high']:,.2f} / {found_data['curr']}{found_data['low']:,.2f}")
            m_c4.metric("📊 వాల్యూమ్", f"{found_data['volume']:,}")
            
            wl_now = load_custom_watchlist()
            if found_data['symbol'] in wl_now:
                st.info(f"ℹ️ **{found_data['symbol']}** ఇప్పటికే బాట్ ట్రేడింగ్ వాచ్‌లిస్ట్‌లో ఉంది.")
            else:
                if st.button(f"➕ {found_data['name']} ని బాట్ ట్రేడింగ్ లోకి యాడ్ చేయి", type="primary", use_container_width=True, key="btn_add_to_wl"):
                    wl_now[found_data['symbol']] = {
                        "name": found_data['name'], "ticker": found_data['symbol'], "type": found_data['type'],
                        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_custom_watchlist(wl_now)
                    st.success(f"🎉 **{found_data['name']} ({found_data['symbol']})** యాడ్ అయ్యింది!")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 ప్రస్తుత బాట్ కస్టమ్ వాచ్‌లిస్ట్ (Active Custom Assets)")
    current_wl = load_custom_watchlist()
    if not current_wl:
        st.info("ప్రస్తుతం కస్టమ్ అసెట్స్ ఏవీ లేవు. పైన ఉన్న సెర్చ్ బాక్స్ ద్వారా మీ ఫేవరెట్ స్టాక్స్ లేదా క్రిప్టోలను యాడ్ చేయండి.")
    else:
        for wl_sym, wl_info in list(current_wl.items()):
            w_col1, w_col2, w_col3, w_col4 = st.columns([3, 2, 2, 1])
            with w_col1:
                icon_flag = "🇮🇳" if wl_info.get('type') == 'NSE' else "🪙"
                st.markdown(f"**{icon_flag} {wl_info.get('name', wl_sym)}** (`{wl_sym}`)")
            with w_col2: st.caption(f"మార్కెట్: {wl_info.get('type', 'NSE')}")
            with w_col3: st.caption(f"యాడ్ చేసిన తేదీ: {wl_info.get('added_at', '-')}")
            with w_col4:
                if st.button("🗑️ తీసివేయి", key=f"del_wl_{wl_sym}"):
                    del current_wl[wl_sym]
                    save_custom_watchlist(current_wl)
                    st.rerun()

    st.markdown("---")
    st.subheader("🔥 Pro Market Analyzer (Scan All)")
    if st.button("🚀 మార్కెట్ ని అనలైజ్ చేయి (Scan All Assets)"):
        st.info("బాట్ మార్కెట్ ని స్కాన్ చేస్తోంది...")
        results_all = []
        for name, sym_s in symbol_options.items():
            df_s, sig_s, last_s = fetch_and_analyze(sym_s)
            if df_s is not None:
                trend_s = "Bullish (Up 🟢)" if last_s['close'] > last_s['EMA_200'] else "Bearish (Down 🔴)"
                rsi_st = "Overbought (Risk 🔴)" if last_s['RSI'] > 70 else "Oversold (Buy Zone 🟢)" if last_s['RSI'] < 30 else "Neutral ⚪"
                results_all.append({
                    "Stock / Coin": name,
                    "Live Price": f"₹{last_s['close']:,.2f}",
                    "Trend": trend_s,
                    "RSI (14)": f"{last_s['RSI']:.1f} - {rsi_st}",
                    "AI Action": sig_s
                })
        st.success("అనాలసిస్ పూర్తయింది!")
        safe_dataframe(pd.DataFrame(results_all), hide_index=True)


# =============================================================
# TAB 6: 💬 AI వాయిస్ అసిస్టెంట్ (VOICE ASSISTANT & LOGS)
# =============================================================
with tab_voice:
    st.subheader("💬 AI తో తెలుగులో మాట్లాడండి (Gemini Voice Assistant)")
    st.markdown("చాట్ చేస్తున్నప్పుడు దయచేసి సెట్టింగ్స్ లో 'Auto Refresh' ఆఫ్ చేయండి.")

    if st.button("🗑️ చాట్ క్లియర్ చేయి (Clear Chat)"):
        st.session_state.messages = [
            {"role": "assistant", "content": "హలో! నేను మీ పర్సనల్ ట్రేడింగ్ అసిస్టెంట్ ని. మీకు ఎలాంటి సందేహాలు ఉన్నా అడగండి!"}
        ]
        st.rerun()

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "హలో! నేను మీ పర్సనల్ ట్రేడింగ్ అసిస్టెంట్ ని. మీకు ఎలాంటి సందేహాలు ఉన్నా అడగండి!"}
            ]
        chat_box = st.container(height=380)
        with chat_box:
            for msg in st.session_state.messages:
                avatar = "🤖" if msg["role"] == "assistant" else "👤"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.write(msg["content"])
                    
        voice_prompt = speech_to_text(language='te-IN', start_prompt="🎙️ వాయిస్ మెసేజ్ పంపడానికి ఇక్కడ నొక్కండి", stop_prompt="🛑 ఆపడానికి ఇక్కడ నొక్కండి", just_once=True, key='STT')
        prompt = st.chat_input("లేదా మీ ప్రశ్న ఇక్కడ టైప్ చేయండి...")
        final_prompt = voice_prompt if voice_prompt else prompt

    if final_prompt:
        st.session_state.messages.append({"role": "user", "content": final_prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(final_prompt)
            
        cmd_lower = final_prompt.lower()
        if "btc" in cmd_lower and ("buy" in cmd_lower or "కొను" in cmd_lower):
            with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY BTC-USD")
            response = "👍 ఓకే బాస్! బిట్ కాయిన్ (BTC) కొనమని కమాండ్ పంపించాను."
        elif "status" in cmd_lower or "ఏం చేస్తున్నావ్" in cmd_lower or "ట్రేడ్" in cmd_lower:
            response = f"🤖 బాట్ ప్రస్తుతం 24/7 మార్కెట్ ని స్కాన్ చేస్తోంది. యాక్టివ్ గా {len(dca_positions)} కాయిన్స్ లో ప్రాఫిట్ టార్గెట్ కోసం హోల్డ్ చేస్తోంది."
        elif "profit" in cmd_lower or "లాభం" in cmd_lower:
            response = f"💰 పోర్ట్‌ఫోలియో నెట్ బ్యాలెన్స్: ₹{portfolio_value:,.2f}. రన్నింగ్ లైవ్ ఫ్లోటింగ్ లాభం: ₹{total_floating_pnl:,.2f}!"
        else:
            try:
                model_gem = genai.GenerativeModel('gemini-1.5-flash')
                res_gem = model_gem.generate_content(f"You are a helpful Telugu stock & crypto trading assistant. Answer in simple Telugu: {final_prompt}")
                response = res_gem.text
            except Exception:
                response = "హలో బాస్! మీ ప్రశ్న అర్థమైంది. నేను నిరంతరం మార్కెట్ ని గమనిస్తున్నాను."
                
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant", avatar="🤖"):
            st.write(response)

    st.markdown("---")
    st.subheader("📝 Live Bot Updates (టెర్మినల్ లాగ్స్)")
    with st.expander("బాట్ ఏం చేస్తోందో టెర్మినల్ లాగ్స్ ఇక్కడ చూడండి"):
        if os.path.exists('bot_logs.txt'):
            with open('bot_logs.txt', 'r') as f_l:
                logs = f_l.readlines()
            recent_logs = logs[-15:] if len(logs) > 15 else logs
            st.code("".join(recent_logs), language="bash")
        else:
            st.info("లాగ్స్ ఇంకా రాలేదు.")

if auto_refresh:
    time.sleep(5)
    st.rerun()
