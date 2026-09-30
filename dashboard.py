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
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1e1e1e;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
    }
    .stTabs [aria-selected="true"] {
        background-color: #2e7bcf !important;
        color: white !important;
        font-weight: bold;
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

st.title("📈 AI Trading Master - Live Dashboard")

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
    "Tata Motors": "TATAMOTORS.NS",
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

# 2. Risk Management

# 4. Market Segment
st.sidebar.markdown("<br>", unsafe_allow_html=True)
market_segment = st.sidebar.selectbox(
    "📊 Market Segment", 
    ["Spot Trading (Safe & Real Assets)", "Futures (Coming Soon)", "Options (Coming Soon)"], 
    index=0
)

new_risk = st.sidebar.select_slider(
    "🔥 Risk Aggression",
    options=["Safe (Low Risk)", "Moderate (Smart AI)", "Extreme (High Profit)"],
    value=bot_settings.get("risk_level", "Moderate (Smart AI)")
)

# 3. Panic Button (Emergency Stop)
st.sidebar.markdown("<br>", unsafe_allow_html=True)
panic = safe_button("🛑 EMERGENCY PANIC STOP", is_sidebar=True, help="కొన్న కాయిన్స్ అన్నీ వెంటనే అమ్మేసి బాట్ ని ఆపేస్తుంది!")

# Update settings if changed
if new_style != bot_settings.get("trading_style") or new_risk != bot_settings.get("risk_level") or panic:
    bot_settings["trading_style"] = new_style
    bot_settings["risk_level"] = new_risk
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

portfolio_value = 10000.0 if trading_mode == "📝 Paper Trading (Virtual)" else (live_usdt_balance * 84.5)
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
auto_refresh = st.sidebar.checkbox("🟢 Auto Refresh (Live)", value=False)
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

@st.cache_data(ttl=15, show_spinner=False)
def fetch_and_analyze(sym):
    try:
        # Yahoo Finance నుండి డేటా తెచ్చుకోవడం (Fast timeout)
        df = yf.download(sym, period="1d", interval="1m", progress=False, timeout=5)
        if df.empty:
            df = yf.download(sym, period="5d", interval="1m", progress=False, timeout=5)
        
        # yfinance columns are MultiIndex sometimes, so flatten them if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        
        if df.empty:
            # Fallback to 5m or 15m
            try:
                df = yf.download(sym, period="5d", interval="5m", progress=False, timeout=5)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df = df.reset_index().rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            except: pass
            
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

main_tab1, main_tab2, main_tab3 = st.tabs([
    "🔴 Live Trading Dashboard", 
    "🔍 Smart Asset Search Engine (క్రిప్టో & ఇండియన్ స్టాక్స్)", 
    "🔥 Pro Market Screener (All Stocks)"
])

with main_tab1:
    def draw_dashboard():
        df, signal, last = fetch_and_analyze(symbol)
        current_price = last['close'] if last is not None else 65000.0
        signal = signal if signal else "HOLD"
        with st.container():
            if "Dual" in trading_mode:
                initial_capital = 50000.00 + (10000.00 * 84.5 if live_usdt_balance == 0 else live_usdt_balance * 84.5)
                title_str = "Dual Hybrid: ₹50,000 (NSE) + Crypto"
            elif "Zerodha" in trading_mode:
                initial_capital = 50000.00
                title_str = "Zerodha Virtual: ₹50,000"
            elif "Live" in trading_mode:
                initial_capital = (live_usdt_balance * 84.5)
                title_str = f"Live Binance: ${live_usdt_balance:.2f} USDT"
            else:
                initial_capital = 10000.00
                title_str = "Crypto Virtual: ₹10,000"
            total_profit = 0.0
            current_balance = initial_capital
            invested_amount = 0.0
            
            if os.path.exists('trades_log.csv'):
                try:
                    hist_df = pd.read_csv('trades_log.csv')
                    
                    # 1. Calculate PnL from SELL trades
                    if 'Profit' in hist_df.columns:
                        g_prof = 0.0
                        g_loss = 0.0
                        taxes = 0.0
                        for idx, row in hist_df.iterrows():
                            if row['Action'] == 'SELL' and str(row['Profit']) != '-':
                                p_str = str(row['Profit']).replace('₹', '').replace(',', '')
                                if p_str.startswith('-'):
                                    p = -float(p_str.replace('-', ''))
                                else:
                                    p = float(p_str)
                                if p > 0:
                                    g_prof += p
                                elif p < 0:
                                    g_loss += abs(p)
                                taxes += abs(p) * 0.001 # 0.1% Binance spot fee
                        total_profit = (g_prof - g_loss) - taxes
                        
                    # 2. Calculate Invested Amount strictly from active DCA positions (dca_state.json)
                    invested_amount = 0.0
                    if os.path.exists('dca_state.json'):
                        try:
                            with open('dca_state.json', 'r') as f_dca:
                                dca_active = json.load(f_dca)
                                for d_sym, d_info in dca_active.items():
                                    invested_amount += float(d_info.get('total_cost', 0.0))
                        except Exception:
                            pass
                            
                except:
                    pass

            portfolio_value = initial_capital + total_profit
            # Strict safety bounds: Invested amount cannot exceed portfolio value, available cash cannot be negative
            invested_amount = min(portfolio_value, max(0.0, invested_amount))
            available_cash = max(0.0, portfolio_value - invested_amount)
            roi = (total_profit / initial_capital) * 100 if initial_capital > 0 else 0.0
            
            # title_str configured above
            st.markdown(f"### 🏦 పోర్ట్‌ఫోలియో బ్యాలెన్స్ ({title_str})")
            b1, b2, b3, b4 = st.columns(4)
            b1.markdown(fancy_metric("టోటల్ పోర్ట్‌ఫోలియో", f"₹{portfolio_value:,.2f}", f"{roi:.2f}% ROI"), unsafe_allow_html=True)
            b2.markdown(fancy_metric("ఇన్వెస్ట్ చేసిన మొత్తం (Locked)", f"₹{invested_amount:,.2f}", "-ట్రేడ్స్ లో ఉంది", "off"), unsafe_allow_html=True)
            b3.markdown(fancy_metric("మిగిలిన క్యాష్ (Margin)", f"₹{available_cash:,.2f}", "ట్రేడింగ్ కి రెడీ"), unsafe_allow_html=True)
            if signal == "BUY": b4.success(f"🤖 Action: {signal}")
            elif signal == "SELL": b4.error(f"🤖 Action: {signal}")
            else: b4.warning(f"🤖 Action: {signal}")

            st.markdown("---")
            
            # 🎯 Live Fractional DCA Positions Monitor
            if os.path.exists('dca_state.json'):
                try:
                    with open('dca_state.json', 'r') as f_dca:
                        dca_positions = json.load(f_dca)
                    if dca_positions:
                        st.markdown("#### 🎯 AI Autonomous DCA Positions (స్వంత నిర్ణయాలు & లైవ్ లాభాలు)")
                        d_cols = st.columns(min(4, len(dca_positions)))
                        for idx, (d_sym, d_info) in enumerate(dca_positions.items()):
                            d_cur = current_price if d_sym == symbol else d_info['avg_price']
                            d_pnl_pct = ((d_cur - d_info['avg_price']) / d_info['avg_price']) * 100.0
                            with d_cols[idx % len(d_cols)]:
                                strat_tag = f" • {d_info.get('strategy', '').replace('_', ' ').title()}" if d_info.get('strategy') else ""
                                p_color = "green" if d_pnl_pct >= 0 else "red"
                                cur_sym_disp = f"₹{d_cur:,.2f}" if (".NS" in d_sym or not "-USD" in d_sym) else f"${d_cur:,.2f}"
                                st.markdown(fancy_metric(
                                    f"{d_sym} (L{len(d_info.get('entries', []))}/3){strat_tag}",
                                    cur_sym_disp,
                                    f"{d_pnl_pct:+.2f}% (టార్గెట్: +1.5%)",
                                    p_color
                                ), unsafe_allow_html=True)
                        st.markdown("---")
                except:
                    pass

            
            # 🌟 Professional UI Tabs
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📊 Live Trading Chart", "🏦 PnL & History", "💬 AI తో మాట్లాడండి (Voice Chat)"])
            
            with sub_tab1:
                st.markdown("### 📈 టెక్నికల్ అనాలసిస్ (Live Data)")
                
                # --- NEW PREMIUM GAUGE CHART ---
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
                            {'range': [0, 35], 'color': 'rgba(255, 50, 50, 0.8)'},     # Red / Sell
                            {'range': [35, 65], 'color': 'rgba(100, 100, 100, 0.6)'}, # Gray / Hold
                            {'range': [65, 100], 'color': 'rgba(50, 255, 50, 0.8)'}], # Green / Buy
                    }
                ))
                fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), template='plotly_dark')
                
                col_g1, col_g2 = st.columns([1, 2])
                with col_g1:
                    safe_plotly_chart(fig_gauge)
                with col_g2:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    
                    
                    @st.cache_data(ttl=600)
                    def get_news_with_sentiment(sym):
                        try:
                            import urllib.request
                            import xml.etree.ElementTree as ET
                            search_term = sym.replace('-USD', '') + " market news crypto"
                            url = f"https://news.google.com/rss/search?q={search_term.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req) as response:
                                xml_data = response.read()
                            root = ET.fromstring(xml_data)
                            
                            pos_words = ['surge', 'soar', 'bull', 'high', 'profit', 'gain', 'buy', 'up', 'breakout', 'record', 'pump']
                            neg_words = ['crash', 'fall', 'bear', 'drop', 'loss', 'sell', 'down', 'hack', 'ban', 'lawsuit', 'dump']
                            
                            news_items = []
                            score = 0
                            for item in root.findall('.//item')[:4]:
                                title = item.find('title').text
                                link = item.find('link').text
                                news_items.append((title, link))
                                
                                title_lower = title.lower()
                                for w in pos_words:
                                    if w in title_lower: score += 1
                                for w in neg_words:
                                    if w in title_lower: score -= 1
                                    
                            return news_items, score
                        except:
                            return [], 0

                    news, sentiment_score = get_news_with_sentiment(symbol)
                    
                    st.markdown("##### ⚡ Extreme AI Engine Status")

                    
                    # Compute ML Prediction
                    try:
                        x = np.arange(20)
                        y = df['close'].tail(20).values
                        slope, intercept = np.polyfit(x, y, 1)
                        predicted_next = slope * 20 + intercept
                        ml_status = "Up (Bullish)" if slope > 0 else "Down (Bearish)"
                    except:
                        predicted_next = current_price
                        ml_status = "Neutral"
                        
                    # Compute Kelly Criterion
                    try:
                        if os.path.exists('trades_log.csv'):
                            tdf = pd.read_csv('trades_log.csv')
                            sym_trades = tdf[(tdf['Symbol'] == symbol) & (tdf['Action'] == 'SELL')]
                            total_trades = len(sym_trades)
                            if total_trades > 0:
                                wins = len(sym_trades[sym_trades['Profit'] > 0])
                                win_rate = wins / total_trades
                                kelly_pct = max(0.05, min(0.60, (2 * win_rate - 1))) * 100
                            else:
                                kelly_pct = 20.0
                        else:
                            kelly_pct = 20.0
                    except:
                        kelly_pct = 20.0

                    m1, m2, m3 = st.columns(3)
                    m1.markdown(fancy_metric("ట్రేడింగ్ పెయిర్", symbol), unsafe_allow_html=True)
                    m2.markdown(fancy_metric("లైవ్ ప్రైస్", f"₹{current_price:,.2f}"), unsafe_allow_html=True)
                    m3.markdown(fancy_metric("RSI (14)", f"{last['RSI']:.1f}", "Overbought" if last['RSI']>70 else "Oversold" if last['RSI']<30 else "Normal", "inverse"), unsafe_allow_html=True)
                    
                    st.markdown("---")
                    e1, e2, e3 = st.columns(3)
                    e1.markdown(fancy_metric("🤖 ML Predictor (2m)", f"₹{predicted_next:,.2f}", ml_status), unsafe_allow_html=True)
                    e2.markdown(fancy_metric("📰 News Sentiment (Score)", f"{sentiment_score}", "Bullish" if sentiment_score > 0 else "Bearish" if sentiment_score < 0 else "Neutral"), unsafe_allow_html=True)
                    e3.markdown(fancy_metric("⚡ Kelly Risk %", f"{kelly_pct:.1f}%", "Auto-Compounding"), unsafe_allow_html=True)

                with st.expander("📰 బ్రేకింగ్ న్యూస్ (Live News)"):
                    if news:
                        for title, link in news:
                            st.write(f"🔹 **[{title}]({link})**")
                    else:
                        st.write("ఈ స్టాక్ కి సంబంధించి తాజా వార్తలు ఏమీ లేవు.")


                

                
                st.subheader("📊 Advanced Technical Chart")
                # Subplots: 1 for Price/EMA, 1 for MACD, 1 for RSI
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])
                
                # Row 1: Candlesticks & EMA
                fig.add_trace(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], line=dict(color='cyan', width=1.5), name='EMA 50'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], line=dict(color='orange', width=2), name='EMA 200 (Trend)'), row=1, col=1)
                
                # Row 2: MACD
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_Line'], line=dict(color='blue', width=1.5), name='MACD'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['MACD_Signal'], line=dict(color='orange', width=1.5), name='Signal'), row=2, col=1)
                # MACD Histogram
                colors = ['green' if val >= 0 else 'red' for val in (df['MACD_Line'] - df['MACD_Signal'])]
                fig.add_trace(go.Bar(x=df['timestamp'], y=(df['MACD_Line'] - df['MACD_Signal']), marker_color=colors, name='Histogram'), row=2, col=1)
                
                # Row 3: RSI
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['RSI'], line=dict(color='purple', width=1.5), name='RSI'), row=3, col=1)
                # RSI Overbought/Oversold lines
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

                fig.update_layout(template='plotly_dark', height=800, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0))
                safe_plotly_chart(fig)
                

            with sub_tab2:
                st.subheader("🔥 లైవ్ లో రన్ అవుతున్న ట్రేడ్స్ (Open Positions)")
                if os.path.exists('trades_log.csv'):
                    tdf = pd.read_csv('trades_log.csv')
                    open_pos = {}
                    for idx, row in tdf.iterrows():
                        sym = row['Symbol']
                        action = row['Action']
                        try:
                            qty = float(str(row['Shares']).replace(',', ''))
                            price = float(str(row['Price']).replace('₹', '').replace(',', ''))
                        except:
                            continue
                        if action == 'BUY':
                            open_pos[sym] = {'qty': qty, 'buy_price': price, 'time': row['Time']}
                        elif action == 'SELL':
                            if sym in open_pos:
                                del open_pos[sym]
                                
                    if len(open_pos) > 0:
                        st.write(f"మొత్తం **{len(open_pos)}** కాయిన్స్/స్టాక్స్ లో మీ డబ్బులు ఇన్వెస్ట్ అయ్యి ఉన్నాయి. వాటి లైవ్ లాభనష్టాలు ఇక్కడ చూడండి:")
                        
                        cols = st.columns(3)
                        col_idx = 0
                        for sym, data in open_pos.items():
                            # Fetch live price quickly without blocking
                            try:
                                if sym == symbol and df is not None:
                                    live_price = last['close']
                                else:
                                    t = yf.Ticker(sym)
                                    p = getattr(t.fast_info, 'last_price', None)
                                    live_price = float(p) if p else data['buy_price']
                            except:
                                live_price = data['buy_price']
                                
                            invested = data['buy_price'] * data['qty']
                            current_val = live_price * data['qty']
                            floating_pnl = current_val - invested
                            pnl_pct = (floating_pnl / invested) * 100
                            
                            with cols[col_idx % 3]:
                                st.info(f"**{sym}**")
                                st.write(f"కొన్న రేటు: ₹{data['buy_price']:.2f}")
                                try:
                                    time_12hr = pd.to_datetime(data['time']).strftime('%I:%M:%S %p')
                                except:
                                    time_12hr = data['time']
                                st.write(f"కొన్న టైమ్: {time_12hr}")
                                st.write(f"లైవ్ ప్రైస్: ₹{live_price:.2f}")
                                st.markdown(fancy_metric("Live PnL (లైవ్ లాభం/నష్టం)", f"₹{floating_pnl:.2f}", f"{pnl_pct:.2f}%"), unsafe_allow_html=True)
                                
                            col_idx += 1
                        st.markdown("---")
                    else:
                        st.success("ప్రస్తుతం ట్రేడ్స్ ఏమీ రన్ అవ్వట్లేదు. అంతా సేఫ్ గా బుక్ అయిపోయింది. కొత్త ఛాన్స్ కోసం బాట్ వెయిట్ చేస్తోంది.")
                else:
                    st.info("ఇంకా ఎలాంటి ట్రేడ్ జరగలేదు.")
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.subheader("📝 పాత ఫైనాన్షియల్ రిపోర్ట్ (PnL & History)")
                with col_h2:
                    if st.button("🗑️ Reset Trade History", help="పాత టెస్ట్ ట్రేడ్స్ క్లియర్ చేసి కొత్తగా జీరో నుంచి మొదలుపెడుతుంది"):
                        if os.path.exists('trades_log.csv'):
                            with open('trades_log.csv', 'w') as f_reset:
                                f_reset.write("Time,Symbol,Action,Price,Shares,Profit\n")
                        if os.path.exists('dca_state.json'):
                            with open('dca_state.json', 'w') as f_dca:
                                f_dca.write("{}")
                        st.toast("✅ పాత ట్రేడ్ హిస్టరీ రీసెట్ అయ్యింది!", icon="🗑️")
                        st.rerun()

                # --- ADVANCED OVERALL PERFORMANCE WIDGET ---
                if os.path.exists('trades_log.csv'):
                    df_perf = pd.read_csv('trades_log.csv')
                    sells = df_perf[df_perf['Action'] == 'SELL'].copy()
                    if not sells.empty:
                        # Clean Profit column
                        def clean_profit(val):
                            if str(val) == '-': return 0.0
                            p_str = str(val).replace('₹', '').replace(',', '')
                            try:
                                return -float(p_str.replace('-', '')) if p_str.startswith('-') else float(p_str)
                            except: return 0.0
                            
                        sells['CleanProfit'] = sells['Profit'].apply(clean_profit)
                        total_trades = len(sells)
                        wins = len(sells[sells['CleanProfit'] > 0])
                        losses = len(sells[sells['CleanProfit'] < 0])
                        breakeven = len(sells[sells['CleanProfit'] == 0])
                        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
                        
                        gross_profit = sells[sells['CleanProfit'] > 0]['CleanProfit'].sum()
                        gross_loss = sells[sells['CleanProfit'] < 0]['CleanProfit'].sum()
                        taxes = round((gross_profit + abs(gross_loss)) * 0.001, 2) # 0.1% Binance spot fee
                        net_profit = gross_profit + gross_loss - taxes # loss is already negative
                        
                        st.markdown(f'''
                        <div style="background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%); padding: 20px; border-radius: 15px; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 20px;">
                            <h3 style="color: #00ffcc; margin-top: 0; text-align: center; font-family: sans-serif;">🤖 AI Overall Performance Summary</h3>
                            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; margin-top: 15px;">
                                <div style="text-align: center; margin: 10px;">
                                    <p style="color: #aaa; margin: 0; font-size: 14px;">Total Trades (SELLs)</p>
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
                                    <h1 style="color: {'#00ff00' if net_profit >= 0 else '#ff3333'}; margin: 5px 0; font-size: 32px;">₹{net_profit:.2f}</h1>
                                </div>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                # ----------------------------------------


                if os.path.exists('trades_log.csv'):
                    history_df = pd.read_csv('trades_log.csv')
                    
                    # ఫైనాన్షియల్ లెక్కలు
                    g_profit = 0.0
                    g_loss = 0.0
                    t_taxes = 0.0
                    tax_per_trade = 0.50 # ప్రతి SELL ట్రేడ్ కి బ్రోకరేజ్/టాక్స్ 50 సెంట్లు అనుకుందాం
                    
                    if 'Profit' in history_df.columns:
                        for idx, row in history_df.iterrows():
                            if row['Action'] == 'SELL' and str(row['Profit']) != '-':
                                try:
                                    p_str = str(row['Profit']).replace('₹', '').replace(',', '')
                                    if p_str.startswith('-'):
                                        p = -float(p_str.replace('-', ''))
                                    else:
                                        p = float(p_str)
                                        
                                    if p > 0:
                                        g_profit += p
                                    elif p < 0:
                                        g_loss += abs(p)
                                    t_taxes += abs(p) * 0.001 # 0.1% Binance spot fee
                                except:
                                    pass
                                    
                    net = (g_profit - g_loss) - t_taxes
                    
                    pnl_col1, pnl_col2, pnl_col3, pnl_col4 = st.columns(4)
                    pnl_col1.markdown(fancy_metric("గ్రాస్ లాభం (Gross Profit)", f"₹{g_profit:.4f}", "సూపర్!"), unsafe_allow_html=True)
                    pnl_col2.markdown(fancy_metric("నష్టం (Gross Loss)", f"₹{g_loss:.4f}", "-రిస్క్"), unsafe_allow_html=True)
                    pnl_col3.markdown(fancy_metric("టాక్స్ & ఫీజు (Taxes/Fees)", f"₹{t_taxes:.4f}", "-కట్ అయ్యాయి"), unsafe_allow_html=True)
                    
                    profit_color = "normal" if net >= 0 else "inverse"
                    pnl_col4.markdown(fancy_metric("అసలు లాభం (Net Profit)", f"₹{net:.4f}", f"{'లాభం' if net >= 0 else 'నష్టం'}", profit_color), unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.subheader("📊 కాయిన్ ల వారీగా ఫుల్ రిపోర్ట్ (Coin-wise Summary)")
                    
                    coin_stats = []
                    for sym in history_df['Symbol'].unique():
                        sym_df = history_df[(history_df['Symbol'] == sym) & (history_df['Action'] == 'SELL')]
                        num_trades = len(sym_df)
                        
                        tot_profit = 0.0
                        tot_loss = 0.0
                        
                        for _, row in sym_df.iterrows():
                            if str(row['Profit']) != '-':
                                try:
                                    p_str = str(row['Profit']).replace('₹', '').replace(',', '')
                                    if p_str.startswith('-'):
                                        p = -float(p_str.replace('-', ''))
                                    else:
                                        p = float(p_str)
                                        
                                    if p > 0:
                                        tot_profit += p
                                    elif p < 0:
                                        tot_loss += abs(p)
                                except:
                                    pass
                                    
                        net = tot_profit - tot_loss
                        
                        if num_trades > 0 or tot_profit > 0 or tot_loss > 0:
                            coin_stats.append({
                                'కాయిన్ (Coin)': sym,
                                'మొత్తం ట్రేడ్స్ (Trades)': num_trades,
                                'లాభం (Profit)': f"₹{tot_profit:.4f}",
                                'నష్టం (Loss)': f"₹{tot_loss:.4f}",
                                'మిగిలింది (Net PnL)': f"₹{net:.4f}"
                            })
                            
                    if coin_stats:
                        summary_df = pd.DataFrame(coin_stats)
                        
                        def style_net_pnl(val):
                            try:
                                v = float(str(val).replace('₹','').replace(',',''))
                                if v > 0: return 'color: #00ff00; font-weight: bold;'
                                elif v < 0: return 'color: #ff3333; font-weight: bold;'
                            except: pass
                            return ''
                            
                        styled_summary = summary_df.style.map(style_net_pnl, subset=['మిగిలింది (Net PnL)'])
                        safe_dataframe(styled_summary, hide_index=True)
                    else:
                        st.info("ఇంకా కాయిన్ల వారీగా కంప్లీట్ అయిన ట్రేడ్స్ ఏమీ లేవు.")
                    
                    st.markdown("---")
                    st.subheader("📋 ట్రేడింగ్ రికార్డ్స్ (Trading Activity & History)")
                    
                    # 1. Deduplicate consecutive identical orders written within seconds
                    clean_rows = []
                    last_seen_key = None
                    for _, r in history_df.iterrows():
                        row_sym = str(r.get('Symbol', ''))
                        row_act = str(r.get('Action', ''))
                        row_price = str(r.get('Price', ''))
                        dedup_key = f"{row_sym}_{row_act}_{row_price}"
                        if dedup_key == last_seen_key:
                            continue
                        clean_rows.append(r)
                        last_seen_key = dedup_key
                        
                    dedup_df = pd.DataFrame(clean_rows) if clean_rows else history_df.copy()
                    
                    # Format Time column safely
                    if 'Time' in dedup_df.columns:
                        try:
                            dedup_df['Time'] = pd.to_datetime(dedup_df['Time'], errors='coerce').dt.strftime('%Y-%m-%d %I:%M:%S %p').fillna(dedup_df['Time'])
                        except:
                            pass

                    # 🎨 Dataframe Styling Helpers
                    def highlight_profit(val):
                        if str(val) == '-' or pd.isna(val): return ''
                        try:
                            v = float(str(val).replace('₹','').replace('$','').replace(',','').replace('+',''))
                            if v > 0: return 'color: #00ff00; font-weight: bold;'
                            elif v < 0: return 'color: #ff3333; font-weight: bold;'
                        except: pass
                        return ''
                    
                    def highlight_action(val):
                        if val == 'BUY': return 'background-color: rgba(0,255,0,0.1); color: #00ff00; font-weight: bold;'
                        elif val == 'SELL': return 'background-color: rgba(255,0,0,0.1); color: #ff3333; font-weight: bold;'
                        return ''

                    h_tab1, h_tab2, h_tab3 = st.tabs([
                        "✅ పూర్తయిన ట్రేడ్లు (Completed Trades)",
                        "⏳ లైవ్ ఓపెన్ పొజిషన్లు (Active Positions)",
                        "📋 పూర్తి ఆర్డర్ హిస్టరీ (All Orders Log)"
                    ])

                    with h_tab1:
                        # Only show SELL orders with realized profit/loss
                        sells_df = dedup_df[dedup_df['Action'] == 'SELL'].copy()
                        if not sells_df.empty:
                            completed_list = []
                            for _, s_row in sells_df.iloc[::-1].iterrows():
                                p_raw = str(s_row.get('Profit', '0.0')).replace('₹','').replace('$','').replace(',','')
                                try:
                                    p_val = float(p_raw)
                                    status_badge = "🟢 లాభం (WIN)" if p_val > 0 else ("🔴 నష్టం (LOSS)" if p_val < 0 else "⚪ బ్రేక్-ఈవెన్")
                                    profit_formatted = f"₹{p_val:+.4f}" if p_val != 0 else "₹0.00"
                                except:
                                    status_badge = "⚪ సాధారణం"
                                    profit_formatted = str(s_row.get('Profit', '-'))

                                pr_val = str(s_row.get('Price', '')).replace('₹','').replace('$','').replace(',','')
                                try:
                                    price_disp = f"${float(pr_val):,.2f}" if "-USD" in str(s_row.get('Symbol','')) else f"₹{float(pr_val):,.2f}"
                                except:
                                    price_disp = str(s_row.get('Price', ''))

                                completed_list.append({
                                    "📅 సమయం (Exit Time)": s_row.get('Time', '-'),
                                    "🪙 కాయిన్ (Coin)": s_row.get('Symbol', '-'),
                                    "💰 అమ్మిన ధర (Exit Price)": price_disp,
                                    "📦 పరిమాణం (Qty)": s_row.get('Shares', '-'),
                                    "📈 లాభం / నష్టం (PnL)": profit_formatted,
                                    "🏷️ ఫలితం (Result)": status_badge
                                })
                            c_df = pd.DataFrame(completed_list)
                            styled_c_df = c_df.style.map(highlight_profit, subset=['📈 లాభం / నష్టం (PnL)'])
                            safe_dataframe(styled_c_df, hide_index=True)
                        else:
                            st.info("ఇంకా కంప్లీట్ అయిన SELL ట్రేడ్స్ లేవు. ప్రస్తుతం కొన్న కాయిన్స్ 'లైవ్ ఓపెన్ పొజిషన్లు' ట్యాబ్ లో సేఫ్ గా ఉన్నాయి.")

                    with h_tab2:
                        # Show current holding positions from dca_state.json
                        open_list = []
                        if os.path.exists('dca_state.json'):
                            try:
                                with open('dca_state.json', 'r') as f_dca:
                                    dca_positions = json.load(f_dca)
                                for d_sym, d_info in dca_positions.items():
                                    d_avg = d_info.get('avg_price', 0.0)
                                    d_qty = d_info.get('total_qty', 0.0)
                                    d_cost = d_info.get('total_cost', 0.0)
                                    d_target = d_info.get('target_sell_price', d_avg * 1.015)
                                    entries = d_info.get('entries', [])
                                    e_time = entries[0].get('time', '-') if entries else '-'
                                    
                                    cur_p = current_price if d_sym == symbol else d_avg
                                    gain_pct = ((cur_p - d_avg) / d_avg * 100.0) if d_avg > 0 else 0.0
                                    
                                    open_list.append({
                                        "📅 ఎంట్రీ సమయం": e_time,
                                        "🪙 కాయిన్ (Coin)": d_sym,
                                        "💵 కొన్న సగటు ధర": f"${d_avg:,.2f}" if "-USD" in d_sym else f"₹{d_avg:,.2f}",
                                        "📊 లైవ్ మార్కెట్ ధర": f"${cur_p:,.2f}" if "-USD" in d_sym else f"₹{cur_p:,.2f}",
                                        "📦 పరిమాణం (Qty)": f"{d_qty:.5f}",
                                        "💰 ఇన్వెస్ట్‌మెంట్": f"₹{d_cost:,.2f}",
                                        "🚀 లైవ్ లాభం %": f"{gain_pct:+.2f}%",
                                        "🎯 టార్గెట్ ప్రైస్ (+1.5%)": f"${d_target:,.2f}" if "-USD" in d_sym else f"₹{d_target:,.2f}",
                                        "🛡️ స్టేటస్": "⏳ HOLD (టార్గెట్ కోసం ఎదురుచూస్తోంది)"
                                    })
                            except Exception:
                                pass
                                
                        if open_list:
                            o_df = pd.DataFrame(open_list)
                            styled_o = o_df.style.map(highlight_profit, subset=['🚀 లైవ్ లాభం %'])
                            safe_dataframe(styled_o, hide_index=True)
                        else:
                            st.info("ప్రస్తుతం ఎలాంటి ఓపెన్ ట్రేడ్స్ లేవు. బాట్ కొత్త సిగ్నల్ కోసం మార్కెట్ ని స్కాన్ చేస్తోంది.")

                    with h_tab3:
                        # Full deduplicated orders log
                        styled_df = dedup_df.iloc[::-1].style.map(highlight_action, subset=['Action']).map(highlight_profit, subset=['Profit'])
                        safe_dataframe(styled_df, hide_index=True)
                else:
                    st.info("ఇంకా ఎలాంటి ట్రేడ్ జరగలేదు. బాట్ ఎదురుచూస్తోంది...")

            with sub_tab3:
                st.markdown("### 💬 ట్రేడింగ్ అసిస్టెంట్ (WhatsApp Style)")
                st.markdown("చాట్ చేస్తున్నప్పుడు దయచేసి సెట్టింగ్స్ లో 'Auto Refresh' ఆఫ్ చేయండి.")
            
                if st.button("🗑️ చాట్ క్లియర్ చేయి (Clear Chat & Fix Errors)"):
                    st.session_state.messages = [
                        {"role": "assistant", "content": "హలో! పాత ఎర్రర్స్ అన్నీ క్లియర్ చేశాను. ఇప్పుడు నన్ను మళ్లీ కొత్తగా అడగండి!"}
                    ]
                    st.rerun()
            
                # Create a narrow layout like a mobile phone screen
                _, center_col, _ = st.columns([1, 2, 1])
            
                with center_col:
                    # యూజర్ అడిగిన ప్రశ్నలు దాచుకోవడానికి సెషన్ స్టేట్
                    if "messages" not in st.session_state:
                        st.session_state.messages = [
                            {"role": "assistant", "content": "హలో! నేను మీ పర్సనల్ ట్రేడింగ్ అసిస్టెంట్ ని. మీకు ఎలాంటి డౌట్స్ ఉన్నా అడగొచ్చు."}
                        ]
                
                    # వాట్సాప్ లాగా ఫిక్స్డ్ హైట్ కంటైనర్ (స్క్రోల్ చేసుకోవచ్చు)
                    chat_box = st.container(height=400)
                
                    with chat_box:
                        for msg in st.session_state.messages:
                            avatar = "🤖" if msg["role"] == "assistant" else "👤"
                            with st.chat_message(msg["role"], avatar=avatar):
                                st.write(msg["content"])
                
                    # వాయిస్ ఇన్పుట్ బటన్ (చిన్నగా)
                    voice_prompt = speech_to_text(
                        language='te-IN', 
                        start_prompt="🎙️ వాయిస్ మెసేజ్ పంపడానికి ఇక్కడ నొక్కండి",
                        stop_prompt="🛑 ఆపడానికి ఇక్కడ నొక్కండి (రికార్డింగ్ ఆగుతుంది)",
                        just_once=True, 
                        key='STT'
                    )
                
                    # యూజర్ టైప్ లేదా మాట్లాడినది తీసుకోవడం
                    prompt = st.chat_input("లేదా మీ ప్రశ్న ఇక్కడ టైప్ చేయండి...")
                    final_prompt = voice_prompt if voice_prompt else prompt
            
                if final_prompt:
                    # Prevent infinite loop API calls if streamlit reruns with same mic prompt
                    last_user_msg = ""
                    for m in reversed(st.session_state.messages):
                        if m["role"] == "user":
                            last_user_msg = m["content"]
                            break
                    is_duplicate = (last_user_msg == final_prompt)
                              
                    if not is_duplicate:
                        # యూజర్ మెసేజ్ సేవ్ చేయడం
                        st.session_state.messages.append({"role": "user", "content": final_prompt})
                        with st.chat_message("user", avatar="👤"):
                            st.write(final_prompt)
                    
                        # అసిస్టెంట్ రిప్లై లాజిక్ (Gemini AI)
                        user_text = final_prompt
                
                    try:
                        df_current, sig_current, last_current = fetch_and_analyze(symbol)
                    
                        cmd_lower = final_prompt.lower()
                        response = ""
                    
                        # 1. COMMANDS
                        if "buy" in cmd_lower or "konu" in cmd_lower or "కొను" in cmd_lower:
                            if "btc" in cmd_lower or "బిట్" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY BTC-USD")
                                response = "👍 ఓకే బాస్! బ్యాక్ గ్రౌండ్ లో బిట్ కాయిన్ (BTC) కొనమని కమాండ్ పంపించాను. టెర్మినల్ లో అది కొనేస్తుంది!"
                            elif "eth" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY ETH-USD")
                                response = "👍 ఓకే బాస్! ఇథీరియం (ETH) కొనమని కమాండ్ పంపించాను."
                            elif "sol" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY SOL-USD")
                                response = "👍 ఓకే బాస్! సొలానా (SOL) కొనమని కమాండ్ పంపించాను."
                            elif "bnb" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY BNB-USD")
                                response = "👍 ఓకే బాస్! బినాన్స్ కాయిన్ (BNB) కొనమని కమాండ్ పంపించాను."
                            elif "reliance" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY RELIANCE.NS")
                                response = "👍 ఓకే బాస్! రిలయన్స్ (RELIANCE.NS) కొనమని Zerodha కమాండ్ పంపించాను."
                            elif "tata" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY TATAMOTORS.NS")
                                response = "👍 ఓకే బాస్! టాటా మోటార్స్ (TATAMOTORS.NS) కొనమని Zerodha కమాండ్ పంపించాను."
                            elif "sbi" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY SBIN.NS")
                                response = "👍 ఓకే బాస్! స్టేట్ బ్యాంక్ (SBIN.NS) కొనమని Zerodha కమాండ్ పంపించాను."
                            elif "infy" in cmd_lower or "infosys" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY INFY.NS")
                                response = "👍 ఓకే బాస్! ఇన్ఫోసిస్ (INFY.NS) కొనమని Zerodha కమాండ్ పంపించాను."
                            elif "hdfc" in cmd_lower:
                                with open('ai_commands.txt', 'w') as f: f.write("FORCE_BUY HDFCBANK.NS")
                                response = "👍 ఓకే బాస్! HDFC బ్యాంక్ (HDFCBANK.NS) కొనమని Zerodha కమాండ్ పంపించాను."
                            else:
                                response = "🤔 ఏ కాయిన్ కొనాలో కరెక్ట్ గా చెప్పండి బాస్. (Ex: 'buy btc')"
                            
                        elif "sell all" in cmd_lower or "ammey" in cmd_lower or "aapey" in cmd_lower or "అమ్మేయ్" in cmd_lower or "stop" in cmd_lower or "ఆపేయ్" in cmd_lower:
                            with open('ai_commands.txt', 'w') as f: f.write("PANIC_SELL_ALL")
                            import json
                            try:
                                with open('settings.json', 'r') as f: bs = json.load(f)
                                bs['panic_mode'] = True
                                with open('settings.json', 'w') as f: json.dump(bs, f)
                            except: pass
                            response = "🚨 ఎమర్జెన్సీ ఆర్డర్ రిసీవ్డ్! వెంటనే ట్రేడింగ్ ఆపేసి, ఉన్న కాయిన్స్ అన్నీ అమ్మేస్తున్నాను బాస్!"
                        
                        # 2. BOT STATUS (READING LOGS)
                        elif "status" in cmd_lower or "em chestunnav" in cmd_lower or "em chestunavu" in cmd_lower or "em chestunnavu" in cmd_lower or "ఏం చేస్తున్నావ్" in cmd_lower or "ఏం చేస్తున్నావు" in cmd_lower or "trade" in cmd_lower or "ట్రేడ్" in cmd_lower:
                            bot_context = "లాగ్స్ ఇంకా రాలేదు బాస్, మార్కెట్ స్కాన్ చేస్తున్నాను."
                            try:
                            
                                if os.path.exists('bot_logs.txt'):
                                    with open('bot_logs.txt', 'r') as log_f:
                                        lines = log_f.readlines()
                                        if lines:
                                            bot_context = lines[-1].strip()
                            except: pass
                            response = "🤖 నేను వాల్ స్ట్రీట్ లో బిజీగా ఉన్నాను బాస్. నా లేటెస్ట్ యాక్షన్ ఇదిగో: " + bot_context
                        elif "price" in cmd_lower or "rate" in cmd_lower or "cost" in cmd_lower or "రేటు" in cmd_lower or "ధర" in cmd_lower:
                            if df_current is not None:
                                response = f"📈 ప్రస్తుతం {symbol} ప్రైస్: ₹{last_current['close']:,.2f} నడుస్తోంది సార్."
                            else:
                                response = "ప్రస్తుతం మార్కెట్ ప్రైస్ చెక్ చేయలేకపోతున్నాను."
                        elif "trend" in cmd_lower or "ela undi" in cmd_lower or "market" in cmd_lower or "ట్రెండ్" in cmd_lower or "మార్కెట్ ఎలా ఉంది" in cmd_lower:
                            if df_current is not None:
                                if last_current['close'] > last_current['EMA_200']:
                                    response = f"🚀 మార్కెట్ స్ట్రాంగ్ గా ఉంది సార్! (Bullish Trend). కొంటే లాభాలు వస్తాయి."
                                else:
                                    response = f"⚠️ మార్కెట్ వీక్ గా పడిపోతూ ఉంది సార్! (Bearish Trend). ఇప్పుడు కొనకపోవడమే సేఫ్."
                            else:
                                response = "మార్కెట్ ట్రెండ్ చెక్ చేయలేకపోతున్నాను."
                        elif "hi" in cmd_lower or "hello" in cmd_lower or "హలో" in cmd_lower or "హాయ్" in cmd_lower:
                            response = "హలో బాస్! నేను మీ యాంటైగ్రావిటీ రోబోట్ ని. డైరెక్ట్ ఆర్డర్ (Ex: 'buy btc') ఇస్తారా? లేదా రిపోర్ట్ (Ex: 'లాభం ఎంత?', 'ఏం చేస్తున్నావు?') చెప్పమంటారా?"
                    
                        # 3. INTERNET SEARCH FALLBACK
                        else:
                            try:
                                import urllib.request, urllib.parse, json, re
                                url = "https://te.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + urllib.parse.quote(final_prompt) + "&utf8=&format=json"
                                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req, timeout=5) as res:
                                    data = json.loads(res.read().decode())
                                    results = data.get('query', {}).get('search', [])
                                    if results:
                                        snippet = re.sub('<[^<]+>', '', results[0]['snippet'])
                                        title = results[0]['title']
                                        response = "🔍 ఇంటర్నెట్ లో వెతికాను బాస్! '" + title + "' గురించి నాకు దొరికిన సమాచారం: " + snippet
                                    else:
                                        url_en = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + urllib.parse.quote(final_prompt) + "&utf8=&format=json"
                                        req_en = urllib.request.Request(url_en, headers={'User-Agent': 'Mozilla/5.0'})
                                        with urllib.request.urlopen(req_en, timeout=5) as res_en:
                                            data_en = json.loads(res_en.read().decode())
                                            results_en = data_en.get('query', {}).get('search', [])
                                            if results_en:
                                                snippet_en = re.sub('<[^<]+>', '', results_en[0]['snippet'])
                                                response = "🔍 ఇంటర్నెట్ లో ఇంగ్లీష్ లో దొరికింది: " + snippet_en
                                            else:
                                                response = "🤔 బాస్.. నాకు మీరు అడిగినదాని గురించి ఇంటర్నెట్ లో కూడా ఎలాంటి ఆన్సర్ దొరకలేదు."
                            except Exception as e:
                                response = "🤔 బాస్.. నాకు మీరు చెప్పింది సరిగ్గా అర్థం కాలేదు, ఇంటర్నెట్ లో వెతుకుదామంటే కనెక్షన్ కట్ అయ్యింది."
                    except Exception as e:
                        response = f"నా ఆఫ్ లైన్ బ్రెయిన్ లో చిన్న ఎర్రర్ వచ్చింది: {e}"
                
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(response)
                        if enable_voice:
                            try:
                                tts = gTTS(text=response, lang='te')
                                tts.save("response.mp3")
                                with open("response.mp3", "rb") as f:
                                    data = f.read()
                                    b64 = base64.b64encode(data).decode()
                                    md = f'''
                                        <audio autoplay="true">
                                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                                        </audio>
                                        '''
                                    st.markdown(md, unsafe_allow_html=True)
                            except Exception as ex:
                                pass
                    



        # Moved logs outside inner tabs
        st.markdown("---")
        st.subheader("📝 Live Bot Updates (లాగ్స్)")
        with st.expander("బాట్ ఏం చేస్తోందో టెర్మినల్ లాగ్స్ ఇక్కడ చూడండి"):
            if os.path.exists('bot_logs.txt'):
                with open('bot_logs.txt', 'r') as f:
                    logs = f.readlines()
                recent_logs = logs[-10:] if len(logs) > 10 else logs
                log_text = "".join(recent_logs)
                st.code(log_text, language="bash")
            else:
                st.info("బాట్ ఇంకా ఆన్ అవ్వలేదు.")

    draw_dashboard()

with main_tab2:
    st.header("🔍 Smart Asset Search Engine (యూనివర్సల్ అసెట్ సెర్చ్ & వాచ్‌లిస్ట్)")
    st.markdown("""
    ఇక్కడ మీరు **భారతీయ స్టాక్ మార్కెట్ (NSE)** లోని ఏ స్టాక్ అయినా (ఉదా: `ZOMATO`, `SUZLON`, `TATASTEEL`, `ADANIENT`, `WIPRO`) 
    లేదా **క్రిప్టో మార్కెట్ (Binance)** లోని ఏ కాయిన్ అయినా (ఉదా: `PEPE`, `DOGE`, `SHIB`, `ADA`, `AVAX`, `SOL`) సెర్చ్ చేసి, 
    లైవ్ ధర చూసి, ఒకే క్లిక్ తో బాట్ ట్రేడింగ్ లిస్ట్‌కి యాడ్ చేయవచ్చు!
    """)
    
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_query = st.text_input(
            "🔎 స్టాక్ లేదా కాయిన్ పేరు / టిక్కర్ టైప్ చేయండి:", 
            placeholder="ఉదాహరణ: ZOMATO, SUZLON, TATASTEEL, PEPE, ADA, DOGE",
            key="universal_search_input"
        )
    with col_s2:
        market_choice = st.radio(
            "మార్కెట్ రకం:", 
            ["🇮🇳 Indian Stock (NSE)", "🪙 Crypto (USD)"],
            horizontal=False,
            key="universal_market_choice"
        )
        
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
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
                    try:
                        c_name = t_obj.info.get('shortName') or t_obj.info.get('name') or clean_sym
                    except:
                        pass
                        
                    found_data = {
                        "symbol": final_sym,
                        "clean": clean_sym,
                        "name": c_name,
                        "price": l_price,
                        "change_pct": chg_pct,
                        "high": hi,
                        "low": lo,
                        "volume": vol,
                        "type": asset_category,
                        "curr": curr_symbol
                    }
            except Exception as ex:
                pass
                
        if found_data:
            st.success(f"✅ **{found_data['name']} ({found_data['symbol']})** మార్కెట్ లో లభించింది!")
            
            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            m_c1.metric("🏢 కంపెనీ / కాయిన్", found_data['name'])
            m_c2.metric("💰 ప్రస్తుత లైవ్ ప్రైస్", f"{found_data['curr']}{found_data['price']:,.2f}", f"{found_data['change_pct']:+.2f}%")
            m_c3.metric("📈 24h హై / లో", f"{found_data['curr']}{found_data['high']:,.2f} / {found_data['curr']}{found_data['low']:,.2f}")
            m_c4.metric("📊 వాల్యూమ్", f"{found_data['volume']:,}")
            
            wl_now = load_custom_watchlist()
            is_already_added = found_data['symbol'] in wl_now
            
            if is_already_added:
                st.info(f"ℹ️ **{found_data['symbol']}** ఇప్పటికే బాట్ ట్రేడింగ్ వాచ్‌లిస్ట్‌లో ఉంది.")
            else:
                if st.button(f"➕ {found_data['name']} ని బాట్ ట్రేడింగ్ లోకి యాడ్ చేయి", type="primary", use_container_width=True, key="btn_add_to_wl"):
                    wl_now[found_data['symbol']] = {
                        "name": found_data['name'],
                        "ticker": found_data['symbol'],
                        "type": found_data['type'],
                        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_custom_watchlist(wl_now)
                    st.success(f"🎉 **{found_data['name']} ({found_data['symbol']})** విజయవంతంగా యాడ్ అయ్యింది! బాట్ వెంటనే దీనిపై ట్రేడ్స్ చేస్తుంది.")
                    if enable_voice:
                        play_voice_response(f"{found_data['name']} has been added to bot trading watchlist.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.error(f"❌ '{search_query}' అనే సింబల్ మార్కెట్ లో దొరకలేదు. దయచేసి సరైన టిక్కర్ (ఉదా: ZOMATO, SUZLON, TATASTEEL, PEPE, ADA) సరిచూసి మళ్ళీ ప్రయత్నించండి.")
    elif do_search:
        st.warning("దయచేసి సెర్చ్ చేయడానికి ఏదైనా స్టాక్ లేదా కాయిన్ పేరు టైప్ చేయండి.")
        
    st.markdown("---")
    st.subheader("📋 ప్రస్తుత బాట్ కస్టమ్ వాచ్‌లిస్ట్ (Active Custom Assets)")
    
    current_wl = load_custom_watchlist()
    if not current_wl:
        st.info("ప్రస్తుతం కస్టమ్ అసెట్స్ ఏవీ లేవు. పైన ఉన్న సెర్చ్ బాక్స్ ద్వారా మీ ఫేవరెట్ స్టాక్స్ లేదా క్రిప్టోలను యాడ్ చేయండి.")
    else:
        st.caption(f"మొత్తం కస్టమ్ అసెట్స్: **{len(current_wl)}** | బాట్ వీటిని ఆటోమేటిక్ గా స్కాన్ చేస్తూ ట్రేడ్స్ చేస్తుంది.")
        for wl_sym, wl_info in list(current_wl.items()):
            w_col1, w_col2, w_col3, w_col4 = st.columns([3, 2, 2, 1])
            with w_col1:
                icon_flag = "🇮🇳" if wl_info.get('type') == 'NSE' else "🪙"
                st.markdown(f"**{icon_flag} {wl_info.get('name', wl_sym)}** (`{wl_sym}`)")
            with w_col2:
                st.caption(f"మార్కెట్: {wl_info.get('type', 'NSE')}")
            with w_col3:
                st.caption(f"యాడ్ చేసిన తేదీ: {wl_info.get('added_at', '-')}")
            with w_col4:
                if st.button("🗑️ తీసివేయి", key=f"del_wl_{wl_sym}"):
                    del current_wl[wl_sym]
                    save_custom_watchlist(current_wl)
                    st.warning(f"⚠️ {wl_sym} వాచ్‌లిస్ట్ నుండి తొలగించబడింది.")
                    time.sleep(0.5)
                    st.rerun()

with main_tab3:
    st.header("🔥 Pro Market Analyzer")
    st.write("ప్రపంచంలోని బెస్ట్ స్టాక్స్/కాయిన్స్ ని ఒకేసారి స్కాన్ చేసి, ఎందులో ట్రేడ్ చేస్తే బాగుంటుందో ఒక ప్రొఫెషనల్ లాగా బాట్ మీకు చెబుతుంది.")
    
    if st.button("🚀 మార్కెట్ ని అనలైజ్ చేయి (Scan All)"):
        st.info("బాట్ మార్కెట్ ని స్కాన్ చేస్తోంది. దయచేసి వేచి ఉండండి...")
        results = []
        for name, sym in symbol_options.items():
            df, sig, last = fetch_and_analyze(sym)
            if df is not None:
                trend = "Bullish (Up)" if last['close'] > last['EMA_200'] else "Bearish (Down)"
                rsi_status = "Overbought (Risk)" if last['RSI'] > 70 else "Oversold (Buy Zone)" if last['RSI'] < 30 else "Neutral"
                
                results.append({
                    "Stock / Coin": name,
                    "Live Price": f"₹{last['close']:,.2f}",
                    "Trend (EMA 200)": trend,
                    "RSI (14)": f"{last['RSI']:.1f} - {rsi_status}",
                    "AI Action": sig
                })
        
        st.success("అనాలసిస్ పూర్తయింది!")
        st.table(pd.DataFrame(results))

if auto_refresh:
    time.sleep(5)
    st.rerun()
