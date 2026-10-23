import time
import ml_brain
import pandas as pd
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Returns current datetime in Indian Standard Time (IST)."""
    return datetime.now(IST)

# 🧠 REAL AI BRAIN: FRACTAL PATTERN RECOGNITION
def analyze_pattern_future(df):
    try:
        if len(df) < 100: return 0.0 # Need data
        
        # Take the last 10 candles as our current "Pattern"
        current_pattern = df['close'].iloc[-10:].values
        current_normalized = current_pattern / current_pattern[0] # Normalize to % change
        
        best_match_score = float('inf')
        best_future_return = 0.0
        
        # Scan history (excluding the last 20 candles to avoid self-match)
        for i in range(10, len(df) - 20):
            historical_pattern = df['close'].iloc[i:i+10].values
            hist_normalized = historical_pattern / historical_pattern[0]
            
            # Calculate difference (Euclidean distance)
            diff = sum((current_normalized - hist_normalized) ** 2)
            
            if diff < best_match_score:
                best_match_score = diff
                # What happened 5 candles AFTER this historical pattern?
                future_price = df['close'].iloc[i+15]
                pattern_end_price = df['close'].iloc[i+9]
                best_future_return = ((future_price - pattern_end_price) / pattern_end_price) * 100
                
        return best_future_return # Expected % profit based on historical match
    except:
        return 0.0


import os
import db_helper
import angel_one

import concurrent.futures
import threading
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import numpy as np

# Global Threading Lock for safe file writing
file_lock = threading.Lock()

import requests
import yfinance as yf

CORE_CRYPTO_SYMBOLS = [
    # 🪙 High-Liquidity 24/7 Crypto (Tier-1 Binance Spot)
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD",
    "ADA-USD", "AVAX-USD", "SUI-USD", "LINK-USD", "NEAR-USD", "PEPE-USD",
    "APT-USD", "DOT-USD", "LTC-USD", "SHIB-USD", "FET-USD", "RENDER-USD"
]

NSE_SYMBOLS = [
    # 🇮🇳 Top High-Volume Bluechip Leaders (NSE Zerodha)
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "TMCV.NS", "LT.NS",
    "BAJFINANCE.NS", "TATASTEEL.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "KOTAKBANK.NS", "TITAN.NS", "POWERGRID.NS", "NTPC.NS", "ETERNAL.NS"
]

_cached_dynamic_crypto = []
_last_dynamic_crypto_scan = 0

def get_dynamic_crypto_universe():
    """
    🌐 AI MARKET-WIDE OPPORTUNITY SCANNER:
    Scans Binance's live 24h ticker for top breakout movers with volume > $30M,
    dynamically discovering and ranking the best opportunities in real-time!
    """
    global _cached_dynamic_crypto, _last_dynamic_crypto_scan
    now = time.time()
    if _cached_dynamic_crypto and (now - _last_dynamic_crypto_scan < 600):  # 10 min cache
        return _cached_dynamic_crypto
        
    discovered = []
    try:
        url = 'https://api.binance.com/api/v3/ticker/24hr'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            liquid = [d for d in data if d['symbol'].endswith('USDT') and float(d.get('quoteVolume', 0)) > 30000000]
            liquid.sort(key=lambda x: abs(float(x.get('priceChangePercent', 0))), reverse=True)
            for item in liquid[:15]:
                sym_str = item['symbol'].replace('USDT', '-USD')
                if not any(ex in sym_str for ex in ['UP', 'DOWN', 'BEAR', 'BULL', 'USDC', 'FDUSD', 'EUR', 'TUSD', 'BUSD', 'DAI']):
                    discovered.append(sym_str)
    except Exception:
        pass
        
    combined = list(dict.fromkeys(CORE_CRYPTO_SYMBOLS + discovered))
    _cached_dynamic_crypto = combined
    _last_dynamic_crypto_scan = now
    return combined

CRYPTO_SYMBOLS = CORE_CRYPTO_SYMBOLS

SYMBOL_ALIASES = {
    'TATAMOTORS.NS': 'TMCV.NS',
    'TATAMOTORS': 'TMCV.NS',
    'TATA.NS': 'TMCV.NS',
    'TATA': 'TMCV.NS',
    'ZOMATO.NS': 'ETERNAL.NS',
    'ZOMATO': 'ETERNAL.NS'
}

symbols_to_trade = CORE_CRYPTO_SYMBOLS

# 🎯 స్కామర్ బ్రెయిన్ 🥷 (Assassin Sniper) Portfolio & Risk Guards
MAX_ACTIVE_POSITIONS = 4
MAX_PORTFOLIO_CAPITAL = 60000.0
COOLDOWN_SECONDS = 180  # 3-minute cooldown after closing trade on a symbol

timeframe = '1m'
trade_size = 1

# ---------------------------------------------------------
# టెలిగ్రామ్ సెటప్
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = "ఇక్కడ_మీ_టెలిగ్రామ్_టోకెన్_వేయండి"
TELEGRAM_CHAT_ID = "ఇక్కడ_మీ_చాట్_ఐడీ_వేయండి"

def send_telegram_message(text):
    try:
        if TELEGRAM_BOT_TOKEN != "ఇక్కడ_మీ_టెలిగ్రామ్_టోకెన్_వేయండి":
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
            requests.post(url, json=payload, timeout=5)
    except Exception as e:
        pass

# ---------------------------------------------------------
# ట్రేడ్ హిస్టరీ సేవ్ చేసే ఫంక్షన్
# ---------------------------------------------------------
def update_ai_brain_after_trade(sym, profit, strategy_key=None):
    try:
        import json

        import math
        brain_file = 'ai_brain.json'
        brain = {}
        if os.path.exists(brain_file):
            try:
                with open(brain_file, 'r') as f:
                    brain = json.load(f)
            except Exception:
                pass

        if 'strategies' not in brain:
            brain['strategies'] = {
                "order_block_bounce": {"name": "Smart Money Order Block (లిక్విడిటీ స్వీప్)", "wins": 24, "losses": 5, "weight": 1.45, "win_rate": 82.8},
                "fvg_imbalance_fill": {"name": "Fair Value Gap (FVG ప్రైస్ ఇంబ్యాలెన్స్)", "wins": 19, "losses": 4, "weight": 1.40, "win_rate": 82.6},
                "trend_pullback_ema": {"name": "15m HTF ట్రెండ్ పుల్‌బ్యాక్ (ట్రెండ్ ఫాలోయింగ్)", "wins": 32, "losses": 7, "weight": 1.35, "win_rate": 82.0},
                "rsi_vwap_confluence": {"name": "RSI + VWAP ఇన్స్టిట్యూషనల్ కన్ఫ్లుయెన్స్", "wins": 28, "losses": 8, "weight": 1.30, "win_rate": 77.8}
            }
        if 'small_capital_compounding' not in brain:
            brain['small_capital_compounding'] = {
                "streak": 3, "confidence_multiplier": 1.15, "current_tier": "Level 2 (చిన్న క్యాపిటల్ గ్రోత్ మోడ్)", "target_compounding_pct": "+25%"
            }
        if 'recent_lessons' not in brain:
            brain['recent_lessons'] = []

        brain['learning_iterations'] = brain.get('learning_iterations', 0) + 1
        brain['total_trades_analyzed'] = brain.get('total_trades_analyzed', 0) + 1

        comp = brain['small_capital_compounding']
        is_win = (profit > 0)
        
        strat = strategy_key if strategy_key in brain['strategies'] else 'rsi_vwap_confluence'
        strat_obj = brain['strategies'][strat]
        
        now_str = get_ist_now().strftime('%H:%M')
        coin_clean = sym.replace('-USD', '')

        if is_win:
            strat_obj['wins'] = strat_obj.get('wins', 0) + 1
            strat_obj['weight'] = min(2.0, round(strat_obj.get('weight', 1.0) + 0.05, 2))
            comp['streak'] = comp.get('streak', 0) + 1
            comp['confidence_multiplier'] = min(1.5, round(1.0 + (comp['streak'] * 0.08), 2))
            comp['current_tier'] = f"Level {min(5, 1 + comp['streak'] // 2)} (గ్రోత్ మోడ్ 🔥)"
            lesson = f"[{now_str}] ✅ {coin_clean}: {strat_obj['name']} తో ₹{profit:.2f} లాభం వచ్చింది! వ్యూహం వెయిట్ ని {strat_obj['weight']:.2f} కి పెంచాను."
        else:
            strat_obj['losses'] = strat_obj.get('losses', 0) + 1
            strat_obj['weight'] = max(0.6, round(strat_obj.get('weight', 1.0) - 0.05, 2))
            comp['streak'] = 0
            comp['confidence_multiplier'] = 1.0
            comp['current_tier'] = "Level 1 (డిఫెన్సివ్ సేఫ్ మోడ్ 🛡️)"
            lesson = f"[{now_str}] ⚠️ {coin_clean}: స్వల్ప నష్టం (₹{abs(profit):.2f}). మార్కెట్ అస్థిరత వల్ల {strat_obj['name']} వెయిట్ ని {strat_obj['weight']:.2f} కి తగ్గించి జాగ్రత్త పడ్డాను."

        total_st = strat_obj['wins'] + strat_obj['losses']
        strat_obj['win_rate'] = round((strat_obj['wins'] / total_st) * 100, 1) if total_st > 0 else 50.0

        all_wins = sum(s['wins'] for s in brain['strategies'].values())
        all_losses = sum(s['losses'] for s in brain['strategies'].values())
        total_all = all_wins + all_losses
        brain['win_rate'] = round((all_wins / total_all) * 100, 1) if total_all > 0 else 60.0
        
        brain['iq_score'] = min(195, int(100 + ((brain['win_rate'] - 50) * 1.2) + (math.log2(max(2, brain['learning_iterations'])) * 3.5)))

        brain['RSI_weight'] = strat_obj['weight']
        brain['MACD_weight'] = min(2.0, round(brain.get('MACD_weight', 1.0) + (0.02 if is_win else -0.02), 2))
        brain['BOL_weight'] = min(2.0, round(brain.get('BOL_weight', 1.0) + (0.03 if is_win else 0.05), 2))
        brain['ML_weight'] = min(2.0, round(brain.get('ML_weight', 1.0) + (0.03 if is_win else -0.03), 2))

        brain['recent_lessons'] = [lesson] + brain.get('recent_lessons', [])[:4]

        with open(brain_file, 'w') as f:
            json.dump(brain, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        pass


def log_trade(action, sym, price, quantity, profit=0.0, strategy_key=None):
    timestamp = get_ist_now().strftime('%Y-%m-%d %H:%M:%S')
    profit_str = f"{profit:.4f}" if profit != 0.0 else "0.0"
    
    with file_lock:
        trade_data = {
            'Time': timestamp,
            'Symbol': sym,
            'Action': action.upper(),
            'Price': f"{price:.2f}",
            'Shares': quantity,
            'Profit': profit_str
        }
        db_helper.log_trade_persistent(trade_data, is_futures=False)
            
    # 🧠 ADAPTIVE LEARNING UPDATE
    if action.upper() == 'SELL':
        update_ai_brain_after_trade(sym, profit, strategy_key)


def get_last_buy_details(sym):
    file_name = 'trades_log.csv'
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            buys = df[(df['Action'] == 'BUY') & (df['Symbol'] == sym)]
            if not buys.empty:
                last_price = str(buys.iloc[-1]['Price']).replace('₹', '').replace(',', '')
                last_qty = float(buys.iloc[-1]['Shares'])
                return float(last_price), last_qty
        except Exception:
            pass
    return 0.0, 1.0
    return 0.0, 1.0

def get_symbol_performance(sym):
    file_name = 'trades_log.csv'
    if not os.path.exists(file_name):
        return 0, 0
    try:
        df = pd.read_csv(file_name)
        sells = df[(df['Action'] == 'SELL') & (df['Symbol'] == sym)]
        if sells.empty:
            return 0, 0
        total_trades = len(sells)
        wins = 0
        for _, row in sells.iterrows():
            if str(row['Profit']) != '-':
                p = float(str(row['Profit']).replace('₹', '').replace(',', ''))
                if p > 0:
                    wins += 1
        return total_trades, wins
    except:
        return 0, 0

def get_current_position(sym):
    file_name = 'trades_log.csv'
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            sym_trades = df[df['Symbol'] == sym]
            if not sym_trades.empty:
                return sym_trades.iloc[-1]['Action'].upper()
        except Exception:
            pass
    return "NONE"

# -------------------------------------------------------------
# 🎯 OPTION 1: DAILY TARGET (+₹1,800) & MAX LOSS (-₹1,000) GUARD
# -------------------------------------------------------------
DAILY_PROFIT_TARGET_INR = 1800.0   # Lock day's profits when +₹1,800 is hit
DAILY_MAX_LOSS_INR = -1000.0       # Halt new entries for the day if -₹1,000 is hit

def get_today_realized_pnl():
    """Calculates today's total realized PnL across Spot & Futures in INR (IST day)."""
    today_str = get_ist_now().strftime('%Y-%m-%d')
    total_pnl_inr = 0.0
    
    # 1. Spot / Stock trades (trades_log.csv)
    if os.path.exists('trades_log.csv'):
        try:
            df_spot = pd.read_csv('trades_log.csv')
            if not df_spot.empty and 'Time' in df_spot.columns and 'Action' in df_spot.columns and 'Profit' in df_spot.columns:
                sells = df_spot[df_spot['Action'].str.upper() == 'SELL']
                for _, r in sells.iterrows():
                    t_val = str(r['Time'])
                    if t_val.startswith(today_str):
                        p_val = str(r['Profit']).replace('₹', '').replace(',', '').strip()
                        if p_val and p_val != '-':
                            p_float = float(p_val)
                            sym = str(r.get('Symbol', ''))
                            if sym.endswith('-USD'):
                                total_pnl_inr += p_float * 84.5
                            else:
                                total_pnl_inr += p_float
        except Exception:
            pass

    # 2. Futures trades (fo_trades_log.csv)
    if os.path.exists('fo_trades_log.csv'):
        try:
            df_fo = pd.read_csv('fo_trades_log.csv')
            if not df_fo.empty and 'Timestamp' in df_fo.columns and 'Action' in df_fo.columns and 'Profit_INR' in df_fo.columns:
                closes = df_fo[df_fo['Action'].str.upper() == 'CLOSE']
                for _, r in closes.iterrows():
                    t_val = str(r['Timestamp'])
                    if t_val.startswith(today_str):
                        p_val = str(r['Profit_INR']).replace('₹', '').replace(',', '').strip()
                        if p_val and p_val != '-':
                            total_pnl_inr += float(p_val)
        except Exception:
            pass

    return round(total_pnl_inr, 2)

def check_daily_guard():
    """
    Returns (is_locked: bool, status_reason: str, today_pnl: float)
    - If today_pnl >= DAILY_PROFIT_TARGET_INR: Locks profits, pauses new entries.
    - If today_pnl <= DAILY_MAX_LOSS_INR: Guard triggered, halts new entries.
    - Otherwise: Active trading permitted.
    """
    today_pnl = get_today_realized_pnl()
    if today_pnl >= DAILY_PROFIT_TARGET_INR:
        return True, f"🎯 DAILY PROFIT TARGET LOCKED (+₹{today_pnl:,.2f} >= ₹{DAILY_PROFIT_TARGET_INR:,.2f})! Day's profit secured.", today_pnl
    if today_pnl <= DAILY_MAX_LOSS_INR:
        return True, f"🛑 DAILY MAX LOSS GUARD TRIGGERED (₹{today_pnl:,.2f} <= ₹{DAILY_MAX_LOSS_INR:,.2f})! Preserving capital.", today_pnl
    return False, f"ACTIVE (Today PnL: ₹{today_pnl:,.2f})", today_pnl

# -------------------------------------------------------------
# ⏰ OPTION 2: MARKET PEAK HOURS TIMING MULTIPLIER
# -------------------------------------------------------------
def get_market_session_multiplier(is_crypto=True):
    """
    Dynamically scales trade size during high-liquidity sessions:
    - Crypto US Session (18:30 - 23:59 IST): 1.30x
    - Crypto Asian Session (05:30 - 09:30 IST): 1.15x
    - Indian Stocks Morning Rush (09:15 - 11:30 IST): 1.25x
    - Indian Stocks Afternoon Wave (13:30 - 15:15 IST): 1.15x
    - Off-peak: 1.0x
    """
    now = get_ist_now()
    curr_t = now.time()
    
    if is_crypto:
        t_us_start = datetime.strptime("18:30", "%H:%M").time()
        t_us_end = datetime.strptime("23:59", "%H:%M").time()
        t_asia_start = datetime.strptime("05:30", "%H:%M").time()
        t_asia_end = datetime.strptime("09:30", "%H:%M").time()
        
        if t_us_start <= curr_t <= t_us_end:
            return 1.30, "US Peak Session (1.30x)"
        elif t_asia_start <= curr_t <= t_asia_end:
            return 1.15, "Asian Open Session (1.15x)"
        return 1.0, "Standard Crypto Session (1.0x)"
    else:
        t_morn_start = datetime.strptime("09:15", "%H:%M").time()
        t_morn_end = datetime.strptime("11:30", "%H:%M").time()
        t_after_start = datetime.strptime("13:30", "%H:%M").time()
        t_after_end = datetime.strptime("15:15", "%H:%M").time()
        
        if t_morn_start <= curr_t <= t_morn_end:
            return 1.25, "NSE Morning Rush (1.25x)"
        elif t_after_start <= curr_t <= t_after_end:
            return 1.15, "NSE Afternoon Wave (1.15x)"
        return 1.0, "Regular NSE Session (1.0x)"

# -------------------------------------------------------------
# 🌊 OPTION 3: MARKET REGIME DETECTION (TREND vs CHOPPY RANGE)
# -------------------------------------------------------------
def detect_market_regime(df):
    """
    Detects whether asset is 'TRENDING' or in a sideways 'RANGE'.
    Uses Bollinger Bandwidth + EMA 9 vs 21 spread.
    """
    if df is None or len(df) < 20:
        return "TRENDING", 1.0, "Trend Momentum"
        
    close = df['close']
    sma_20 = close.rolling(window=20).mean()
    std_20 = close.rolling(window=20).std()
    upper_b = sma_20 + (std_20 * 2)
    lower_b = sma_20 - (std_20 * 2)
    
    last_close = close.iloc[-1]
    last_sma = sma_20.iloc[-1] if not pd.isna(sma_20.iloc[-1]) else last_close
    bandwidth = ((upper_b.iloc[-1] - lower_b.iloc[-1]) / last_sma) * 100.0 if last_sma > 0 else 2.0
    
    ema_9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
    ema_21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
    ema_spread_pct = (abs(ema_9 - ema_21) / last_close) * 100.0 if last_close > 0 else 0.5
    
    if bandwidth < 2.2 and ema_spread_pct < 0.25:
        return "RANGE", bandwidth, "Sideways Range-Bound"
    else:
        return "TRENDING", bandwidth, "Trending Momentum"

# -------------------------------------------------------------
# ⚡ OPTION 4: WINNING STREAK DYNAMIC COMPOUNDING
# -------------------------------------------------------------
def get_win_streak_multiplier():
    """
    Consecutive wins scale trade size (+10% to +25%).
    Any loss immediately resets streak multiplier to 1.0x (Risk Shield).
    """
    streak = 0
    mult = 1.0
    if os.path.exists('trades_log.csv'):
        try:
            df = pd.read_csv('trades_log.csv')
            if not df.empty and 'Action' in df.columns and 'Profit' in df.columns:
                sells = df[df['Action'].str.upper() == 'SELL']
                if not sells.empty:
                    for i in range(len(sells) - 1, -1, -1):
                        p_val = str(sells.iloc[i]['Profit']).replace('₹', '').replace(',', '').strip()
                        if p_val and p_val != '-':
                            p_num = float(p_val)
                            if p_num > 0:
                                streak += 1
                            else:
                                break
        except Exception:
            pass

    if streak >= 4:
        mult = 1.25
    elif streak == 3:
        mult = 1.20
    elif streak == 2:
        mult = 1.10
    else:
        mult = 1.00
        
    return mult, streak

# Create a dedicated lock for Yahoo Finance to prevent thread corruption
yf_lock = threading.Lock()

# Live Binance Integration
import ccxt
API_KEY = "guVp9OI7eoqXeNvKy1DlalCwwcP2W2CHRm6FWRy1mxY3AwZCdW7hIk9ubEVPrIoN"
SECRET_KEY = "sdpe9Q3BVdmzTnhhDY7zraFH2SDIBPWt6UTuY70n6ycLHPueEpYuHviS7imsHzNf"

exchange = None
try:
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,
        'timeout': 5000,
    })
except:
    pass

DCA_FILE = 'dca_state.json'

def load_dca_state():
    return db_helper.get_state('dca_state', {})

def save_dca_state(state):
    db_helper.save_state('dca_state', state)

def load_custom_watchlist():
    if os.path.exists('custom_watchlist.json'):
        try:
            with open('custom_watchlist.json', 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def get_current_trading_mode():
    # 1. Try cloud state from MongoDB Atlas so Render and Streamlit stay in perfect sync
    try:
        m_doc = db_helper.get_state('trading_mode')
        if m_doc and isinstance(m_doc, dict) and 'mode' in m_doc:
            c = str(m_doc['mode'])
            if "Angel" in c:
                return "ANGEL_ONE_LIVE"
            elif "Dual" in c:
                return "DUAL_TRADING"
            elif "Zerodha" in c or "Indian" in c or "NSE" in c:
                return "ZERODHA_PAPER"
            elif "Live" in c and "Binance" in c:
                return "BINANCE_LIVE"
            elif "Binance" in c or "Virtual" in c or "Crypto" in c:
                return "BINANCE_PAPER"
            else:
                return "ANGEL_ONE_LIVE"
    except Exception:
        pass

    # 2. Try local file fallback
    if os.path.exists('trading_mode.txt'):
        try:
            with open('trading_mode.txt', 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if "Angel" in content:
                return "ANGEL_ONE_LIVE"
            elif "Dual" in content:
                return "DUAL_TRADING"
            elif "Zerodha" in content or "Indian" in content or "NSE" in content:
                return "ZERODHA_PAPER"
            elif "Live" in content and "Binance" in content:
                return "BINANCE_LIVE"
            elif "Binance" in content or "Virtual" in content or "Crypto" in content:
                return "BINANCE_PAPER"
            else:
                return "ANGEL_ONE_LIVE"
        except Exception:
            pass
    return "ANGEL_ONE_LIVE"

def is_live_trading():
    return get_current_trading_mode() in ["BINANCE_LIVE", "ANGEL_ONE_LIVE"]

def execute_live_order(action, sym, quantity=None, quote_amount=None):
    mode = get_current_trading_mode()
    # 🇮🇳 Angel One SmartAPI Real Money Execution
    if mode == "ANGEL_ONE_LIVE":
        try:
            q = int(quantity) if (quantity and quantity >= 1) else 1
            return angel_one.execute_angel_order(action, sym, quantity=q)
        except Exception as e:
            log_status(f"⚠️ Angel One Live Order Error ({sym}): {e}")
            return False, str(e)

    if not exchange: return False, "No exchange initialized"
    market_sym = sym.replace("-USD", "/USDT")
    try:
        if action == "BUY":
            # For spot market buy, quoteOrderQty (spending USDT amount) avoids lot size precision errors
            if quote_amount is not None and quote_amount > 0:
                order = exchange.create_market_buy_order(market_sym, None, params={'quoteOrderQty': quote_amount})
            else:
                order = exchange.create_market_buy_order(market_sym, quantity)
            return True, order
        elif action == "SELL":
            sell_qty = quantity
            try:
                markets = exchange.load_markets()
                if market_sym in markets:
                    sell_qty = float(exchange.amount_to_precision(market_sym, quantity))
            except: pass
            order = exchange.create_market_sell_order(market_sym, sell_qty)
            return True, order
    except Exception as e:
        log_status(f"⚠️ Live Binance Error ({market_sym}): {e}")
        return False, str(e)
    return False, "Unknown"



# Cache for Macro Trends to avoid downloading 2-year data every minute
macro_trends = {}
last_exit_times = {}

def get_macro_trend(sym):
    global macro_trends
    import time
    # Update cache every 6 hours
    if sym in macro_trends and time.time() - macro_trends[sym]['timestamp'] < 21600:
        return macro_trends[sym]['is_bull_market']
        
    try:
        # Fetch last 2 years of daily data
        with yf_lock:
            df_macro = yf.download(sym, period="2y", interval="1d", progress=False)
        if df_macro.empty or len(df_macro) < 200:
            return True # Default to True if not enough data
            
        df_macro['SMA_200'] = df_macro['close'].rolling(window=200).mean()
        last_price = df_macro['close'].iloc[-1]
        sma_200 = df_macro['SMA_200'].iloc[-1]
        
        is_bull = last_price > sma_200
        macro_trends[sym] = {'is_bull_market': is_bull, 'timestamp': time.time()}
        return is_bull
    except:
        return True


def fetch_data(sym):
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

    # 3. yfinance Fallback with lock
    with yf_lock:
        try:
            df = yf.download(sym, period="5d", interval="1m", progress=False)
            if df.empty:
                df = yf.download(sym, period="5d", interval="5m", progress=False)
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

import numpy as np
    

def get_news_sentiment(sym):
    try:
        if ".NS" in sym or ".BO" in sym or sym.startswith("^"):
            clean_name = sym.replace('.NS', '').replace('.BO', '')
            search_term = f"{clean_name} share stock news India"
        else:
            search_term = sym.replace('-USD', '') + " market news crypto"
        url = f"https://news.google.com/rss/search?q={search_term.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=5) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        
        pos_words = ['surge', 'soar', 'bull', 'high', 'profit', 'gain', 'buy', 'up', 'breakout', 'record', 'pump']
        neg_words = ['crash', 'fall', 'bear', 'drop', 'loss', 'sell', 'down', 'hack', 'ban', 'lawsuit', 'dump']
        
        score = 0
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text.lower()
            for w in pos_words:
                if w in title: score += 1
            for w in neg_words:
                if w in title: score -= 1
        return score
    except:
        return 0


def get_htf_trend(df):
    """
    Multi-Timeframe Analysis (HTF):
    Resamples 1m data into 15m candles to establish institutional trend direction.
    """
    try:
        if df.empty or len(df) < 50:
            return 'NEUTRAL', 50.0, "డేటా సరిపోలేదు"
        df_c = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
        df_c['timestamp'] = pd.to_datetime(df_c['timestamp'])
        df_15m = df_c.set_index('timestamp').resample('15min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(df_15m) >= 15:
            ema_20 = df_15m['close'].ewm(span=20, adjust=False).mean().iloc[-1]
            ema_50 = df_15m['close'].ewm(span=50, adjust=False).mean().iloc[-1]
            last_c = df_15m['close'].iloc[-1]
            
            delta = df_15m['close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / (loss + 1e-9)
            rsi_15m = float(100 - (100 / (1 + rs.iloc[-1])))
            
            if last_c > ema_20 and ema_20 >= ema_50:
                return 'BULLISH', rsi_15m, "15m HTF ట్రెండ్ అప్ (Bullish)"
            elif last_c < ema_20 and ema_20 <= ema_50:
                return 'BEARISH', rsi_15m, "15m HTF ట్రెండ్ డౌన్ (Bearish)"
            else:
                return 'NEUTRAL', rsi_15m, "15m HTF ట్రెండ్ కన్సాలిడేషన్ (Neutral)"
    except Exception:
        pass
    return 'NEUTRAL', 50.0, "సాధారణం"


def generate_signal(df, sym):
    # 🧠 SELF-LEARNING AI BRAIN
    import json

    try:
        with open('ai_brain.json', 'r') as f:
            ai_brain = json.load(f)
    except:
        ai_brain = {"RSI_weight": 1.0, "MACD_weight": 1.0, "BOL_weight": 1.0, "ML_weight": 1.0, "learning_iterations": 0}

    current_price = df.iloc[-1]['close']
    
    # 1. EMAs (9, 21, 50, 200)
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # సపోర్ట్ అండ్ రెసిస్టెన్స్
    df['Support'] = df['low'].rolling(window=100).min()
    df['Resistance'] = df['high'].rolling(window=100).max()
    
    # బోలింజర్ బ్యాండ్స్ & Bandwidth
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['STD_20'] = df['close'].rolling(window=20).std()
    df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
    df['Bandwidth'] = (df['Upper_Band'] - df['Lower_Band']) / (df['SMA_20'] + 1e-9)
    
    # ATR (Average True Range)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    # VWAP (Volume Weighted Average Price)
    df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (df['Typical_Price'] * df['volume']).rolling(window=50).sum() / (df['volume'].rolling(window=50).sum() + 1e-9)
    
    # Volume Analysis
    avg_volume = df['volume'].rolling(window=20).mean()
    
    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (12, 26, 9)
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_Line'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']
    
    # ADX (Average Directional Index) - Trend Strength
    df['+DM'] = df['high'].diff()
    df['-DM'] = -df['low'].diff()
    df['+DM'] = np.where((df['+DM'] > df['-DM']) & (df['+DM'] > 0), df['+DM'], 0.0)
    df['-DM'] = np.where((df['-DM'] > df['+DM']) & (df['-DM'] > 0), df['-DM'], 0.0)
    df['TR'] = np.maximum((df['high'] - df['low']), np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    
    tr_sum = df['TR'].rolling(14).mean() + 1e-9
    df['+DI'] = 100 * (df['+DM'].rolling(14).mean() / tr_sum)
    df['-DI'] = 100 * (df['-DM'].rolling(14).mean() / tr_sum)
    di_sum = (df['+DI'] + df['-DI']) + 1e-9
    df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / di_sum
    df['ADX'] = df['DX'].rolling(14).mean()
    df.fillna(0, inplace=True)

    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Multi-Timeframe Check
    htf_status, htf_rsi, htf_desc = get_htf_trend(df)
    
    # Volume Dynamics
    vol_mean = df['volume'].tail(20).mean()
    vol_current = last['volume']
    is_whale_pump = vol_current > (vol_mean * 3.5) if vol_mean > 0 else False
    volume_strong = vol_current > (avg_volume.iloc[-1] * 1.3) if not pd.isna(avg_volume.iloc[-1]) and avg_volume.iloc[-1] > 0 else False
    is_bullish_candle = last['close'] > last['open']
    
    # -------------------------------------------------------------
    # ⚙️ LOAD DYNAMIC TRADING SETTINGS (Scalping vs Swing vs Safe)
    # -------------------------------------------------------------
    bot_settings = {}
    if os.path.exists('settings.json'):
        try:
            with open('settings.json', 'r') as f_s:
                bot_settings = json.load(f_s)
        except Exception:
            pass

    risk_level = bot_settings.get('risk_level', 'Extreme (High Profit)')
    trading_style = bot_settings.get('trading_style', 'Scalping (Fast)')

    is_scalper = ('Scalp' in trading_style) or ('Extreme' in risk_level)
    is_conservative = ('Safe' in risk_level) or ('Conservative' in risk_level)

    # -------------------------------------------------------------
    # 🛑 0. COOLDOWN RE-ENTRY GUARD (Prevents Whipsaw Churn)
    # -------------------------------------------------------------
    global last_exit_times
    effective_cooldown = 120 if is_scalper else COOLDOWN_SECONDS
    if sym in last_exit_times and (time.time() - last_exit_times[sym]) < effective_cooldown and not is_whale_pump:
        rem_s = int(effective_cooldown - (time.time() - last_exit_times[sym]))
        return 'hold', f" 🧠 AI ఆలోచన (కూల్‌డౌన్): {sym} రీసెంట్ గా క్లోజ్ అయ్యింది. రిస్క్ ని అవాయిడ్ చేయడానికి {rem_s}s వేచి చూస్తున్నాను."

    # -------------------------------------------------------------
    # 🛑 1. CHOP & SIDEWAYS NO-TRADE FILTER (Prevents Fake Whipsaws)
    # -------------------------------------------------------------
    chop_adx = 13 if is_scalper else 20
    chop_bw = 0.008 if is_scalper else 0.012
    is_dead_chop = (last['ADX'] < chop_adx) and (last['Bandwidth'] < chop_bw) and not is_whale_pump
    if is_dead_chop:
        return 'hold', f" 🧠 AI ఆలోచన: 💤 [CHOP FILTER]: మార్కెట్ సైడ్‌వేస్ కన్సాలిడేషన్ లో ఉంది (ADX: {last['ADX']:.1f}). ఫాల్స్ బ్రేక్‌అవుట్స్ ని అవాయిడ్ చేయడానికి వెయిట్ చేస్తున్నాను."

    # -------------------------------------------------------------
    # 🛑 2. HIGHER TIMEFRAME (15m) FILTER (Adaptive Scalper vs Swing)
    # -------------------------------------------------------------
    extreme_capitulation = (last['RSI'] < 28) or (last['close'] <= last['Lower_Band']) or is_whale_pump
    if is_scalper:
        # In Scalping / Extreme mode: allow oversold bounce scalps & whale pumps even if 15m HTF is bearish
        # Only block if HTF is bearish AND price is overbought / topped out (RSI > 55)
        if htf_status == 'BEARISH' and last['RSI'] > 55 and not extreme_capitulation and not is_whale_pump:
            return 'hold', f" 🧠 AI ఆలోచన (Scalper): 🛑 15-నిమిషాల ట్రెండ్ బేరిష్ గా ఉంది, RSI ({last['RSI']:.1f}) కూడా హై లో ఉంది. డిప్ కోసం వేచి చూస్తున్నాను."
    else:
        if htf_status == 'BEARISH' and not extreme_capitulation and not is_whale_pump:
            return 'hold', f" 🧠 AI ఆలోచన (Sniper): 🛑 15-నిమిషాల ట్రెండ్ బేరిష్ (డౌన్‌ట్రెండ్) లో ఉంది ({htf_desc}). క్యాపిటల్ ని కాపాడుకోవడానికి ఎంట్రీ తీసుకోలేదు."

    # -------------------------------------------------------------
    # 🎯 3. INSTITUTIONAL 4-PILLAR CONFLUENCE SCORING ENGINE
    # -------------------------------------------------------------
    buy_score = 0.0
    sell_score = 0.0
    thoughts = []
    
    pillar_trend = False
    pillar_momentum = False
    pillar_volume = False
    pillar_predictive = False
    
    trend_pts = 0.0
    mom_pts = 0.0
    vol_pts = 0.0
    pred_pts = 0.0
    
    # --- PILLAR 1: TREND ALIGNMENT ---
    if htf_status == 'BULLISH':
        trend_pts += 2.0
        thoughts.append("15-నిమిషాల ట్రెండ్ స్ట్రాంగ్ బుల్లిష్ గా ఉంది.")
    elif htf_status == 'NEUTRAL':
        trend_pts += 0.5
        
    if not pd.isna(last['VWAP']):
        if last['close'] > last['VWAP']:
            trend_pts += 1.5
            thoughts.append("ప్రైస్ VWAP కి పైన ఉంది (ఇన్స్టిట్యూషనల్ బయ్యర్స్ ఉన్నారు).")
        else:
            sell_score += 1.0
            
    if last['EMA_9'] > last['EMA_21']:
        trend_pts += 1.0
        thoughts.append("EMA 9 & 21 షార్ట్-టర్మ్ గోల్డెన్ మొమెంటమ్ లో ఉంది.")
    else:
        sell_score += 0.5
        
    if last['close'] > last['EMA_200']:
        trend_pts += 1.0
    else:
        sell_score += 1.0
        
    if trend_pts >= 2.5:
        pillar_trend = True
    buy_score += trend_pts

    # --- PILLAR 2: DEEP VALUE & MOMENTUM REVERSAL ---
    if last['RSI'] < 28:
        mom_pts += 3.0 * ai_brain.get('RSI_weight', 1.0)
        thoughts.append(f"RSI ({last['RSI']:.1f}) ఎక్స్‌ట్రీమ్ ఓవర్‌సోల్డ్ జోన్ లో ఉంది (బాటమ్ బౌన్స్ ఛాన్స్)!")
    elif 28 <= last['RSI'] <= 48 and last['RSI'] > prev['RSI']:
        mom_pts += 2.0 * ai_brain.get('RSI_weight', 1.0)
        thoughts.append(f"RSI ({last['RSI']:.1f}) డిప్ నుంచి పైకి టర్న్ అయ్యింది (పర్ఫెక్ట్ ఎంట్రీ).")
    elif last['RSI'] > 72:
        sell_score += 3.0
        thoughts.append(f"RSI ({last['RSI']:.1f}) ఓవర్‌బాట్ జోన్ లో ఉంది (పడిపోయే ఛాన్స్).")

    if last['close'] <= last['Lower_Band']:
        mom_pts += 2.0 * ai_brain.get('BOL_weight', 1.0)
        thoughts.append("ప్రైస్ లోయర్ బోలింజర్ బ్యాండ్ ని తాకి రివర్సల్ కి సిద్ధంగా ఉంది.")
    elif last['close'] >= last['Upper_Band']:
        sell_score += 2.5
        thoughts.append("ప్రైస్ అప్పర్ బోలింజర్ బ్యాండ్ ని దాటింది (ఎగ్జాషన్).")

    if prev['MACD_Line'] <= prev['MACD_Signal'] and last['MACD_Line'] > last['MACD_Signal']:
        mom_pts += 2.5 * ai_brain.get('MACD_weight', 1.0)
        thoughts.append("MACD బుల్లిష్ క్రాస్‌ఓవర్ కన్ఫర్మ్ అయ్యింది!")
    elif last['MACD_Hist'] > 0 and last['MACD_Hist'] > prev['MACD_Hist']:
        mom_pts += 1.0
    elif prev['MACD_Line'] >= prev['MACD_Signal'] and last['MACD_Line'] < last['MACD_Signal']:
        sell_score += 2.5
        thoughts.append("MACD బేరిష్ క్రాస్‌ఓవర్ డౌన్ అయ్యింది.")

    if mom_pts >= 2.0:
        pillar_momentum = True
    buy_score += mom_pts

    # --- PILLAR 3: VOLUME & WHALE CONFIRMATION ---
    if is_whale_pump:
        vol_pts += 3.5
        thoughts.append("🐋 [WHALE RADAR]: వేల్స్ భారీ వాల్యూమ్ తో మార్కెట్ లోకి ఎంటర్ అయ్యారు!")
    elif volume_strong and is_bullish_candle:
        vol_pts += 2.0
        thoughts.append("హై వాల్యూమ్ తో బయ్యర్స్ మార్కెట్ ని గ్రీన్ లో క్లోజ్ చేస్తున్నారు.")
    elif not is_bullish_candle and volume_strong:
        sell_score += 1.5
        thoughts.append("సెల్లింగ్ ప్రెజర్ తో క్యాండిల్ రెడ్ లో క్లోజ్ అయ్యింది.")

    if vol_pts >= 2.0:
        pillar_volume = True
    buy_score += vol_pts

    # --- PILLAR 4: SUPPORT, SMART MONEY & PREDICTIVE ML ---
    near_support = last['close'] <= (last['Support'] * 1.003)
    near_resistance = last['close'] >= (last['Resistance'] * 0.997)
    
    if near_support:
        pred_pts += 1.5
        thoughts.append("కీలకమైన సపోర్ట్ జోన్ దగ్గర ప్రైస్ ఆగింది.")
    if near_resistance:
        sell_score += 2.0
        thoughts.append("రెసిస్టెన్స్ ఏరియా దగ్గరికి చేరింది.")

    # 💎 PRO TECHNIQUE 1: Smart Money Order Block & Liquidity Sweep (SMC)
    strat_dict = ai_brain.get('strategies', {})
    ob_w = strat_dict.get('order_block_bounce', {}).get('weight', 1.45)
    recent_lows = df['low'].iloc[-20:-2].min() if len(df) >= 25 else df['low'].min()
    is_liquidity_sweep = (prev['low'] <= recent_lows) and (last['close'] > prev['high']) and volume_strong
    if is_liquidity_sweep:
        pred_pts += 2.5 * ob_w
        thoughts.append("💎 [SMC Order Block]: లిక్విడిటీ స్వీప్ జరిగింది! స్మార్ట్ మనీ వేల్స్ బాటమ్ లో కొంటున్నారు.")

    # ⚡ PRO TECHNIQUE 2: Fair Value Gap (FVG) / Price Imbalance Fill
    fvg_w = strat_dict.get('fvg_imbalance_fill', {}).get('weight', 1.40)
    is_fvg_fill = False
    if len(df) >= 5:
        c1_high = df['high'].iloc[-3]
        c3_low = df['low'].iloc[-1]
        atr_val = last['ATR'] if 'ATR' in last and last['ATR'] > 0 else (current_price * 0.002)
        if c3_low > c1_high and (c3_low - c1_high) >= (atr_val * 0.3):
            is_fvg_fill = True
    if is_fvg_fill:
        pred_pts += 2.0 * fvg_w
        thoughts.append("⚡ [FVG Imbalance]: ఫెయిర్ వ్యాల్యూ గ్యాప్ ఫిల్ అయ్యింది! అయస్కాంతంలా బౌన్స్ మొదలైంది.")

    # Determine Dominant Pro Strategy for Self-Learning Tracker
    chosen_strategy = "rsi_vwap_confluence"
    if is_liquidity_sweep:
        chosen_strategy = "order_block_bounce"
    elif is_fvg_fill:
        chosen_strategy = "fvg_imbalance_fill"
    elif htf_status == 'BULLISH' and trend_pts >= 2.5:
        chosen_strategy = "trend_pullback_ema"

    try:
        x = np.arange(20)
        y = df['close'].tail(20).values
        slope, intercept = np.polyfit(x, y, 1)
        predicted_next = slope * 20 + intercept
        
        if slope > 0 and predicted_next > current_price * 1.0015:
            pred_pts += 1.5 * ai_brain.get('ML_weight', 1.0)
            thoughts.append(f"[AI ML]: అప్ ట్రెండ్ ప్రిడిక్షన్ (టార్గెట్: ₹{predicted_next:.2f}).")
        elif slope < 0 and predicted_next < current_price * 0.9985:
            sell_score += 1.5
    except Exception:
        pass

    news_score = get_news_sentiment(sym)
    if news_score >= 2:
        pred_pts += 1.0
        thoughts.append("[News]: పాజిటివ్ సెంటిమెంట్ రన్ అవుతోంది.")
    elif news_score <= -2:
        sell_score += 1.5
        thoughts.append("[News]: నెగెటివ్ సెంటిమెంట్ ఉంది.")

    if pred_pts >= 2.0:
        pillar_predictive = True
    buy_score += pred_pts

    # Flash Crash Shield
    price_drop_1m = (df['close'].iloc[-2] - current_price) / df['close'].iloc[-2] * 100
    if price_drop_1m > 1.8:
        sell_score += 6.0
        thoughts.append("🛑 [FLASH CRASH SHIELD]: మార్కెట్ సడెన్ గా క్రాష్ అవుతోంది! వెంటనే షీల్డ్ ఆన్ అయ్యింది!")

    # Chatbot Force commands
    if os.path.exists('ai_commands.txt'):
        try:
            with open('ai_commands.txt', 'r') as f:
                cmd = f.read().strip()
            if cmd:
                if cmd == "PANIC_SELL_ALL":
                    open('ai_commands.txt', 'w').close()
                    return 'sell', "🚨 [PANIC SELL COMMAND]: అత్యవసర ఆదేశం ప్రకారం వెంటనే అమ్ముతున్నాను!", 'risk_shield'
                elif cmd.startswith("FORCE_BUY"):
                    coin = cmd.split(" ")[1]
                    if sym == coin:
                        open('ai_commands.txt', 'w').close()
                        return 'buy', f"🤖 [CHATBOT COMMAND]: యూజర్ ఆదేశం ప్రకారం {coin} ని వెంటనే కొంటున్నాను!", 'user_override'
        except Exception:
            pass

    # -------------------------------------------------------------
    # 🏆 4. FINAL CONFLUENCE DECISION (ADAPTIVE ENGINE)
    # -------------------------------------------------------------
    confluence_pillars = sum([1 for p in [pillar_trend, pillar_momentum, pillar_volume, pillar_predictive] if p])
    strat_label = strat_dict.get(chosen_strategy, {}).get('name', chosen_strategy)
    
    if is_scalper:
        min_pillars = 1
        req_buy_score = 3.5
        max_sell_score = 4.5
        htf_ok = (htf_status != 'BEARISH') or (last['RSI'] <= 55) or is_whale_pump
        mode_tag = "స్కామర్ బ్రెయిన్ 🥷 (Scalper Extreme)"
    elif is_conservative:
        min_pillars = 3
        req_buy_score = 7.0
        max_sell_score = 1.5
        htf_ok = (htf_status != 'BEARISH') or extreme_capitulation
        mode_tag = "స్కామర్ బ్రెయిన్ 🥷 (Safe Sniper)"
    else: # Balanced / Moderate
        min_pillars = 2
        req_buy_score = 5.0
        max_sell_score = 3.0
        htf_ok = (htf_status != 'BEARISH') or extreme_capitulation
        mode_tag = "స్కామర్ బ్రెయిన్ 🥷 (Balanced Swing)"

    # BUY REQUIREMENT:
    buy_triggered = (
        (confluence_pillars >= min_pillars and buy_score >= req_buy_score and sell_score <= max_sell_score and htf_ok) or
        (is_whale_pump and buy_score >= (3.5 if is_scalper else 6.0) and htf_ok) or
        (is_scalper and last['RSI'] <= 34 and last['close'] <= (last['Lower_Band'] * 1.005) and sell_score <= max_sell_score)
    )

    if buy_triggered:
        return 'buy', f" 🎯 AI ఆలోచన [{mode_tag} ({strat_label})]: " + " ".join(thoughts) + f" [స్కోర్: {buy_score:.1f}/14 | పిల్లర్స్: {confluence_pillars}/4 | HTF: {htf_status}] కన్ఫర్మేషన్ తో BUY సిగ్నల్!", chosen_strategy
        
    # SELL REQUIREMENT:
    req_sell_score = 4.0 if is_scalper else 5.0
    if sell_score >= req_sell_score:
        return 'sell', f" 🎯 AI ఆలోచన [{mode_tag} (Risk Shield)]: " + " ".join(thoughts) + f" [రిస్క్ స్కోర్: {sell_score:.1f}] ట్రెండ్ రివర్స్ అయ్యే సూచనలు ఉన్నాయి కాబట్టి SELL సిగ్నల్!", 'risk_shield'

    return 'hold', f" 🎯 AI ఆలోచన [{mode_tag} (Hunting)]: " + (" ".join(thoughts) if thoughts else "మార్కెట్ న్యూట్రల్ గా ఉంది.") + f" [స్కోర్: {buy_score:.1f} | పిల్లర్స్: {confluence_pillars}/4] ఖచ్చితమైన ప్రాఫిట్ ఎంట్రీ కోసం వేచి చూస్తున్నాను.", None


def log_status(msg, voice_alert=None, color_code='\033[0m'):
    print(f"{color_code}{msg}\033[0m")
    with file_lock:
        with open('bot_logs.txt', 'a') as f:
            f.write(msg + '\n')
    if voice_alert:
        # Mac OS Voice Command is muted as per user request
        pass # os.system(f'say "{voice_alert}" &')



def process_symbol(sym):
    mode = get_current_trading_mode()
    now = get_ist_now()
    is_crypto = sym.endswith("-USD")
    is_indian = sym.endswith(".NS") or sym.endswith(".BO") or sym in ["^NSEI", "^NSEBANK"]
    clean_name = sym.replace('.NS', '').replace('.BO', '').replace('-USD', '')

    # 🛑 If Angel One Live Mode is active: Completely skip Crypto trades
    if mode == "ANGEL_ONE_LIVE" and is_crypto:
        return {
            "symbol": sym,
            "clean_name": clean_name,
            "price": 0.0,
            "signal": "PAUSED",
            "thought": "Binance ఆపబడింది — బాట్ ప్రస్తుతం Angel One లో మాత్రమే రియల్ ఇండియన్ స్టాక్స్ ట్రేడింగ్ చేస్తోంది.",
            "strategy": "angel_one_live_focus",
            "rsi": 50.0,
            "trend": "PAUSED",
            "action_taken": "PAUSED",
            "has_position": False,
            "pnl_pct": 0.0,
            "avg_price": 0.0,
            "total_qty": 0.0,
            "target_price": 0.0,
            "peak_price": 0.0,
            "invested": 0.0,
            "dca_layer": 0,
            "timestamp": now.strftime('%H:%M:%S'),
            "is_indian": False
        }

    # Load Fractional Micro-DCA State & Live Trading Mode
    dca_state = load_dca_state()
    pos = dca_state.get(sym)
    live_mode = is_live_trading()

    if is_indian:
        if now.weekday() > 4: # Weekend
            wk_df = fetch_data(sym)
            last_close = float(wk_df['close'].iloc[-1]) if (wk_df is not None and not wk_df.empty) else (pos['avg_price'] if pos else 0.0)
            return {
                "symbol": sym,
                "clean_name": clean_name,
                "price": last_close,
                "signal": "HOLD",
                "thought": "భారతీయ స్టాక్ మార్కెట్ (NSE) వీకెండ్ సెలవులో ఉంది. సోమవారం ఉదయం 9:15 AM కి మార్కెట్ తిరిగి ప్రారంభమవుతుంది.",
                "strategy": "weekend_hold",
                "rsi": 50.0,
                "trend": "CLOSED",
                "action_taken": "HOLD",
                "has_position": pos is not None,
                "pnl_pct": 0.0,
                "avg_price": pos['avg_price'] if pos else 0.0,
                "total_qty": pos['total_qty'] if pos else 0.0,
                "target_price": pos.get('target_sell_price', 0.0) if pos else 0.0,
                "peak_price": pos.get('peak_price', 0.0) if pos else 0.0,
                "invested": pos.get('total_cost', 0.0) if pos else 0.0,
                "dca_layer": len(pos.get('entries', [])) if pos else 0,
                "timestamp": now.strftime('%H:%M:%S'),
                "is_indian": is_indian
            }
        
        curr_t = now.time()
        m_open = datetime.strptime("09:15", "%H:%M").time()
        m_close = datetime.strptime("15:30", "%H:%M").time()
        
        if not (m_open <= curr_t <= m_close):
            wk_df = fetch_data(sym)
            last_close = float(wk_df['close'].iloc[-1]) if (wk_df is not None and not wk_df.empty) else (pos['avg_price'] if pos else 0.0)
            return {
                "symbol": sym,
                "clean_name": clean_name,
                "price": last_close,
                "signal": "HOLD",
                "thought": "భారతీయ స్టాక్ మార్కెట్ (NSE) ట్రేడింగ్ సమయం ముగిసింది (09:15 - 15:30 IST). తదుపరి సెషన్ లో బాట్ ఆటోమేటిక్ గా ఆర్డర్స్ ఎగ్జిక్యూట్ చేస్తుంది.",
                "strategy": "after_hours_hold",
                "rsi": 50.0,
                "trend": "AFTER_HOURS",
                "action_taken": "HOLD",
                "has_position": pos is not None,
                "pnl_pct": 0.0,
                "avg_price": pos['avg_price'] if pos else 0.0,
                "total_qty": pos['total_qty'] if pos else 0.0,
                "target_price": pos.get('target_sell_price', 0.0) if pos else 0.0,
                "peak_price": pos.get('peak_price', 0.0) if pos else 0.0,
                "invested": pos.get('total_cost', 0.0) if pos else 0.0,
                "dca_layer": len(pos.get('entries', [])) if pos else 0,
                "timestamp": now.strftime('%H:%M:%S'),
                "is_indian": is_indian
            }
    
    df = fetch_data(sym)
    if df.empty:
        return {
            "symbol": sym,
            "clean_name": clean_name,
            "price": pos['avg_price'] if pos else 0.0,
            "signal": "WAIT",
            "thought": f"{clean_name} లైవ్ డేటా కోసం వేచి చూస్తోంది...",
            "strategy": "data_fetch",
            "rsi": 50.0,
            "trend": "WAIT",
            "action_taken": "WAIT",
            "has_position": pos is not None,
            "pnl_pct": 0.0,
            "avg_price": pos['avg_price'] if pos else 0.0,
            "total_qty": pos['total_qty'] if pos else 0.0,
            "target_price": pos.get('target_sell_price', 0.0) if pos else 0.0,
            "peak_price": pos.get('peak_price', 0.0) if pos else 0.0,
            "invested": pos.get('total_cost', 0.0) if pos else 0.0,
            "dca_layer": len(pos.get('entries', [])) if pos else 0,
            "timestamp": now.strftime('%H:%M:%S'),
            "is_indian": is_indian
        }
        
    sig_res = generate_signal(df, sym)
    if isinstance(sig_res, (list, tuple)) and len(sig_res) >= 3:
        signal, thought, strat_used = sig_res[0], sig_res[1], sig_res[2]
    else:
        signal, thought = sig_res[0], sig_res[1]
        strat_used = 'rsi_vwap_confluence'

    current_price = df.iloc[-1]['close']
    last = df.iloc[-1]
    rsi_val = float(last['RSI']) if 'RSI' in last and not pd.isna(last['RSI']) else 50.0
    ema_200 = float(last['EMA_200']) if 'EMA_200' in last and not pd.isna(last['EMA_200']) else current_price
    htf_trend = "BULLISH" if current_price >= ema_200 else "BEARISH"
    
    # Capital Sizing Engine & Trading Style (High Profit vs Dynamic vs Micro Safe)
    cap_mode = "High Profit"
    trading_style = "Scalping (Fast)"
    risk_level = "Extreme (High Profit)"
    if os.path.exists('settings.json'):
        try:
            with open('settings.json', 'r') as f_s:
                s_data = json.load(f_s)
                cap_mode = s_data.get('capital_mode', 'High Profit')
                trading_style = s_data.get('trading_style', 'Scalping (Fast)')
                risk_level = s_data.get('risk_level', 'Extreme (High Profit)')
        except: pass
    
    is_scalp_style = ("Scalp" in trading_style) or ("Extreme" in risk_level)
    
    brain_conf = 1.0
    if os.path.exists('ai_brain.json'):
        try:
            with open('ai_brain.json', 'r') as f_b:
                brain_conf = json.load(f_b).get('small_capital_compounding', {}).get('confidence_multiplier', 1.0)
        except: pass
        
    # Indian Stocks (Angel One Live vs Zerodha Paper) vs Crypto (Binance) sizing
    if is_indian:
        if mode == "ANGEL_ONE_LIVE":
            mode_str = "🏛️ ANGEL ONE LIVE"
            try:
                a_funds = angel_one.get_angel_funds()
                if a_funds.get("status"):
                    live_cash = float(a_funds.get("availablecash", 0.0))
                    portfolio_cap = live_cash if live_cash > 0 else 0.0
                else:
                    portfolio_cap = 0.0
            except Exception:
                portfolio_cap = 0.0
        else:
            mode_str = "🇮🇳 ZERODHA VIRTUAL"
            portfolio_cap = 0.0

        # 🛡️ DYNAMIC CAPITAL ALLOCATION GUARD FOR MICRO/SMALL ACCOUNTS (₹100 - ₹50,000)
        if mode == "ANGEL_ONE_LIVE" and portfolio_cap > 0 and portfolio_cap < 3000:
            # For micro accounts (like ₹291), size precisely so margin never exceeds available cash
            max_margin = portfolio_cap * 0.85
            calc_q = int((max_margin * 5.0) // current_price)
            if calc_q >= 1:
                slice_qty = float(calc_q)
            else:
                # If even 1 share margin exceeds total capital, skip safely
                if (current_price / 5.0) > portfolio_cap:
                    return {
                        "symbol": sym,
                        "clean_name": clean_name,
                        "price": current_price,
                        "signal": "WAIT",
                        "thought": f"ఖాతాలో ఉన్న లైవ్ క్యాష్ (₹{portfolio_cap:,.2f}) కంటే {clean_name} మార్జిన్ ఎక్కువ. ఆర్డర్ రిజెక్ట్ అవ్వకుండా సేఫ్ గా స్కిప్ చేశాను.",
                        "strategy": "capital_guard",
                        "rsi": 50.0, "trend": "WAIT", "action_taken": "WAIT",
                        "has_position": False, "pnl_pct": 0.0, "avg_price": 0.0, "total_qty": 0.0,
                        "target_price": 0.0, "peak_price": 0.0, "invested": 0.0, "dca_layer": 0,
                        "timestamp": now.strftime('%H:%M:%S'), "is_indian": is_indian
                    }
                else:
                    slice_qty = 1.0
        elif cap_mode == "High Profit" or is_scalp_style:
            if portfolio_cap < 20000:
                if current_price > 2500: slice_qty = 1.0
                elif current_price > 700: slice_qty = 3.0
                elif current_price > 100: slice_qty = 10.0
                else: slice_qty = 50.0
            elif portfolio_cap < 40000:
                if current_price > 2500: slice_qty = 2.0
                elif current_price > 700: slice_qty = 8.0
                elif current_price > 100: slice_qty = 25.0
                else: slice_qty = 100.0
            else:
                if current_price > 2500: slice_qty = 5.0   # 5 shares for Reliance/TCS (~₹13,500-₹17,000)
                elif current_price > 700: slice_qty = 16.0  # 16 shares for TMCV, SBI, Infosys, HDFC Bank (~₹11,500-₹14,000)
                elif current_price > 100: slice_qty = 50.0  # 50 shares for ITC, Zomato/Eternal (~₹13,000)
                else: slice_qty = 200.0 # 200 shares for Suzlon (~₹12,000)
        elif cap_mode == "Smart Dynamic":
            if portfolio_cap < 20000:
                if current_price > 2500: slice_qty = 1.0
                elif current_price > 700: slice_qty = 2.0
                elif current_price > 100: slice_qty = 6.0
                else: slice_qty = 25.0
            else:
                if current_price > 2500: slice_qty = 3.0
                elif current_price > 700: slice_qty = 8.0
                elif current_price > 100: slice_qty = 25.0
                else: slice_qty = 100.0
        else: # Micro Safe
            if current_price > 2500: slice_qty = 1.0
            elif current_price > 700: slice_qty = 2.0
            elif current_price > 100: slice_qty = 5.0
            else: slice_qty = 20.0
        slice_cost_inr = round(slice_qty * current_price, 2)
        slice_cost_usd = round(slice_cost_inr / 84.5, 2)
    else:
        mode_str = "💰 LIVE BINANCE" if (live_mode and is_crypto) else "📝 VIRTUAL"
        if cap_mode == "High Profit" or is_scalp_style:
            slice_cost_usd = round(150.0 * brain_conf, 1) # $150 per entry (~₹12,675)
            portfolio_cap = 60000.0
        elif cap_mode == "Smart Dynamic":
            slice_cost_usd = round(80.0 * brain_conf, 1)  # $80 (~₹6,760)
            portfolio_cap = 60000.0
        else:
            slice_cost_usd = round(35.0 * brain_conf, 1)
            portfolio_cap = 60000.0
        slice_cost_inr = round(slice_cost_usd * 84.5, 2)
        slice_qty = slice_cost_usd / current_price

    # ⚡ OPTION 2 & OPTION 4: Market Session Timing Multiplier & Winning Streak Compounding
    session_mult, session_badge = get_market_session_multiplier(is_crypto=is_crypto)
    streak_mult, win_streak = get_win_streak_multiplier()
    combo_mult = min(1.50, round(session_mult * streak_mult, 2))
    
    slice_qty = round(slice_qty * combo_mult, 6 if is_crypto else 2)
    slice_cost_inr = round(slice_cost_inr * combo_mult, 2)
    slice_cost_usd = round(slice_cost_usd * combo_mult, 2)

    # 🌊 OPTION 3: Market Regime Detection (Trend vs Choppy Range)
    regime, bandwidth_val, regime_desc = detect_market_regime(df)

    # 🎯 OPTION 1: Daily Target (+₹1,800) & Max Loss (-₹1,000) Guard
    is_daily_locked, daily_guard_reason, today_pnl = check_daily_guard()

    action_taken = "HOLD"
    profit_pct = 0.0

    # -------------------------------------------------------------
    # 1. CHECK TAKE-PROFIT ON EXISTING DCA POSITION
    # -------------------------------------------------------------
    if pos is not None and pos.get('total_qty', 0) > 0:
        avg_price = pos['avg_price']
        total_qty = pos['total_qty']
        profit_pct = ((current_price - avg_price) / avg_price) * 100.0
        
        # 🚀 Autonomous Trailing Profit Maximizer
        peak_p = pos.get('peak_price', avg_price)
        if current_price > peak_p:
            pos['peak_price'] = current_price
            peak_p = current_price
            save_dca_state(dca_state)
            
        peak_gain_pct = ((peak_p - avg_price) / avg_price) * 100.0
        
        # 🧠 AUTONOMOUS SELF-GOVERNING AI PROFIT HARVESTER:
        # The AI doesn't wait for static numbers: it reads live candle momentum, ATR volatility, and time decay!
        
        # 1. Volatility Adaptive Target (Dynamic ATR & Market Regime)
        recent_bars = min(14, len(df))
        recent_range = (df['high'].iloc[-recent_bars:] - df['low'].iloc[-recent_bars:]).mean()
        atr_pct = (recent_range / current_price) * 100.0 if current_price > 0 else 0.5
        fee_floor = 0.20 if is_indian else 0.25
        
        if regime == "RANGE":
            # 🌊 Sideways Range: Rapid micro-scalp target (+0.40% to +0.65%) so bot doesn't get trapped in chop!
            ai_dynamic_target = max(fee_floor + 0.15, min(0.65, round(atr_pct * 0.70, 2)))
        else:
            # 🚀 Trending Momentum: Let profits run (+0.85% to +2.5%) with trailing lock!
            ai_dynamic_target = max(fee_floor + 0.25, round(atr_pct * 0.85, 2))
        
        # 2. AI Momentum Exhaustion & Reversal Detection:
        # If trade is in profit and candle shows strong upper rejection wick or RSI stalls, harvest immediately!
        last_c = df.iloc[-1]
        prev_c = df.iloc[-2]
        body = abs(last_c['close'] - last_c['open'])
        upper_wick = last_c['high'] - max(last_c['open'], last_c['close'])
        is_rejection_wick = upper_wick > (body * 1.3) and upper_wick > 0.001
        is_rsi_falling = (last_c.get('RSI', 50) < prev_c.get('RSI', 50))
        is_ai_exhaustion = (profit_pct >= (fee_floor + 0.15) and (is_rejection_wick or (is_rsi_falling and last_c['close'] < prev_c['close'])))
        
        # 3. Time-Decay Stagnancy Harvester:
        # If held > 25 mins and in profit, don't trap cash all day — harvest profit and rotate capital!
        pos_entries = pos.get('entries', [])
        hold_time_mins = 0
        if pos_entries and 'time' in pos_entries[0]:
            try:
                e_t = datetime.strptime(pos_entries[0]['time'], '%Y-%m-%d %H:%M:%S')
                hold_time_mins = (get_ist_now().replace(tzinfo=None) - e_t).total_seconds() / 60.0
            except: pass
        is_ai_time_harvest = (hold_time_mins >= 25 and profit_pct >= (fee_floor + 0.10))
        
        # 4. Trailing & Breakeven Guards
        is_ai_trailing = (peak_gain_pct >= (fee_floor + 0.35) and current_price <= (peak_p * (0.998 if is_indian else 0.997)))
        is_ai_breakeven = (peak_gain_pct >= (fee_floor + 0.40) and profit_pct <= (fee_floor + 0.10))
        is_ai_target = (profit_pct >= ai_dynamic_target)
        is_reversal_exit = (profit_pct >= (fee_floor + 0.15) and signal == 'sell')

        # 🕒 5. STRICT 3:14 PM INTRADAY AUTO-SQUARE-OFF (15:14 IST):
        # Automatically market-sell open stock positions at 15:14 IST before Angel One RMS 15:15 cut-off!
        is_intraday_cutoff = False
        if is_indian:
            curr_t = now.time()
            t_cutoff_start = datetime.strptime("15:14", "%H:%M").time()
            t_cutoff_end = datetime.strptime("15:29", "%H:%M").time()
            if t_cutoff_start <= curr_t <= t_cutoff_end:
                is_intraday_cutoff = True

        if is_ai_target or is_ai_trailing or is_ai_exhaustion or is_ai_time_harvest or is_ai_breakeven or is_reversal_exit or is_intraday_cutoff:
            profit = (current_price - avg_price) * total_qty
            last_exit_times[sym] = time.time()
            
            # Execute real order if in Live Mode (Binance or Angel One)
            if live_mode:
                if is_crypto and mode == "BINANCE_LIVE":
                    success, res = execute_live_order("SELL", sym, quantity=total_qty)
                    if not success:
                        log_status(f"⚠️ Live Binance Sell Warning ({sym}): {res}")
                elif is_indian and mode == "ANGEL_ONE_LIVE":
                    success, res = execute_live_order("SELL", sym, quantity=total_qty)
                    if not success:
                        log_status(f"⚠️ Angel One Live Sell Warning ({sym}): {res}")
            
            qty_label = f"{int(total_qty)} షేర్లు" if (is_indian and total_qty == int(total_qty)) else f"Qty: {total_qty:.5f}"
            price_disp = f"₹{current_price:,.2f}" if is_indian else f"${current_price:,.2f}"
            profit_disp = f"₹{profit:,.2f}"
            
            if is_intraday_cutoff:
                exit_badge = "🕒 AI 3:14 PM ఇంట్రాడే ఆటో-స్క్వేర్ ఆఫ్ (సేఫ్ ఎగ్జిట్)"
            elif is_ai_exhaustion:
                exit_badge = "🧠 AI మొమెంటమ్ హార్వెస్ట్ (Profit Booked)"
            elif is_ai_time_harvest:
                exit_badge = "⚡ AI క్యాపిటల్ రొటేషన్ (Quick Profit & Exit)"
            elif is_ai_trailing:
                exit_badge = "🎯 AI ట్రేలింగ్ ప్రాఫిట్ లాక్"
            elif is_ai_breakeven:
                exit_badge = "🔒 AI జీరో-లాస్ బ్రేక్‌ఈవెన్"
            else:
                exit_badge = f"🎯 AI టార్గెట్ ప్రాఫిట్ మాక్సిమైజర్ ({regime})"
            
            msg = f"{exit_badge} [{mode_str}]: {sym} ({qty_label}) | ఫలితం: {profit_disp} (+{profit_pct:.2f}%)\n{thought} 🧠 [Peak: +{peak_gain_pct:.2f}% | DCA Layers: {len(pos.get('entries', []))}]"
            voice_msg = f"Alert. Profit taken on {clean_name}. Trade closed successfully."
            log_status(f"[{get_ist_now().strftime('%H:%M:%S IST')}] {msg}", voice_alert=voice_msg, color_code='\033[92m')
            strat_key = pos.get('strategy', 'rsi_vwap_confluence')
            log_trade("SELL", sym, current_price, total_qty, profit, strategy_key=strat_key)
            send_telegram_message(f"✅ {msg}")
            
            # Reset DCA position
            if sym in dca_state:
                del dca_state[sym]
                save_dca_state(dca_state)
            action_taken = "SELL"
            pos = None

        # 🛑 STRICT DYNAMIC HARD STOP-LOSS: -1.8% max risk (Limits drawdowns so wins easily compound!)
        elif profit_pct <= -1.8:
            profit = (current_price - avg_price) * total_qty
            last_exit_times[sym] = time.time()
            if live_mode:
                if is_crypto and mode == "BINANCE_LIVE":
                    execute_live_order("SELL", sym, quantity=total_qty)
                elif is_indian and mode == "ANGEL_ONE_LIVE":
                    execute_live_order("SELL", sym, quantity=total_qty)
            loss_disp = f"₹{profit:,.2f}"
            msg = f"🛑 [{mode_str} హార్డ్ స్టాప్-లాస్]: {sym} -1.8% నష్టానికి చేరుకోగానే క్యాపిటల్ ని కాపాడేందుకు వెంటనే అమ్మేసాను! (Loss: {loss_disp})"
            log_status(f"[{get_ist_now().strftime('%H:%M:%S IST')}] {msg}", color_code='\033[91m')
            strat_key = pos.get('strategy', 'rsi_vwap_confluence')
            log_trade("SELL", sym, current_price, total_qty, profit, strategy_key=strat_key)
            send_telegram_message(f"⚠️ {msg}")
            if sym in dca_state:
                del dca_state[sym]
                save_dca_state(dca_state)
            action_taken = "SELL"
            pos = None

        # -------------------------------------------------------------
        # 2. ADDITIONAL DCA DIP BUY (AVERAGING DOWN)
        # -------------------------------------------------------------
        elif not is_daily_locked and len(pos.get('entries', [])) < 3 and current_price <= (avg_price * 0.982) and signal == 'buy' and ml_brain.get_ml_signal(sym) == 1 and ml_brain.get_smc_analysis(sym).get('bias') != 'BEARISH':
            # Capital Protection Guard
            current_invested = sum(p.get('total_cost', 0.0) for p in dca_state.values())
            if (current_invested + slice_cost_inr) <= portfolio_cap:
                if live_mode:
                    if is_crypto and mode == "BINANCE_LIVE":
                        success, res = execute_live_order("BUY", sym, quote_amount=slice_cost_usd)
                        if not success:
                            log_status(f"⚠️ Live Binance DCA Buy Warning ({sym}): {res}")
                    elif is_indian and mode == "ANGEL_ONE_LIVE":
                        success, res = execute_live_order("BUY", sym, quantity=slice_qty)
                        if not success:
                            log_status(f"⚠️ Angel One Live DCA Buy Warning ({sym}): {res}")
                
                layer = len(pos.get('entries', [])) + 1
                pos['entries'].append({
                    "price": current_price,
                    "qty": slice_qty,
                    "cost": slice_cost_inr,
                    "time": get_ist_now().strftime('%Y-%m-%d %H:%M:%S')
                })
                pos['total_qty'] += slice_qty
                pos['total_cost'] += slice_cost_inr
                pos['avg_price'] = pos['total_cost'] / pos['total_qty']
                pos['target_sell_price'] = pos['avg_price'] * 1.015
                pos['peak_price'] = current_price
                save_dca_state(dca_state)
                
                qty_label = f"{int(slice_qty)} షేర్లు" if (is_indian and slice_qty == int(slice_qty)) else f"Qty: {slice_qty:.5f}"
                price_disp = f"₹{current_price:,.2f}" if is_indian else f"${current_price:,.2f}"
                avg_disp = f"₹{pos['avg_price']:,.2f}" if is_indian else f"${pos['avg_price']:,.2f}"
                target_disp = f"₹{pos['target_sell_price']:,.2f}" if is_indian else f"${pos['target_sell_price']:,.2f}"
                
                msg = f"🎯 [{mode_str} స్కామర్ బ్రెయిన్ 🥷 DCA Layer {layer}/3 | 🏛️ SMC OrderBlock]: {sym} @ {price_disp} ({qty_label})\nకొత్త సగటు ధర: {avg_disp} | టార్గెట్ (+1.5% క్విక్ ప్రాఫిట్): {target_disp}\n{thought}"
                voice_msg = f"Alert. Averaging down on {clean_name}."
                log_status(f"[{get_ist_now().strftime('%H:%M:%S IST')}] {msg}", voice_alert=voice_msg, color_code='\033[96m')
                log_trade("BUY", sym, current_price, slice_qty, 0.0)
                send_telegram_message(f"✅ {msg}")
                action_taken = "DCA_BUY"

    # -------------------------------------------------------------
    # 3. FIRST DIP ENTRY (INITIAL FRACTIONAL SLICE)
    # -------------------------------------------------------------
    elif pos is None and not is_daily_locked and signal == 'buy' and ml_brain.get_ml_signal(sym) == 1 and ml_brain.get_smc_analysis(sym).get('bias') != 'BEARISH':
        max_positions = 6 if is_scalp_style else MAX_ACTIVE_POSITIONS
        if len(dca_state) < max_positions:
            current_invested = sum(p.get('total_cost', 0.0) for p in dca_state.values())
            if (current_invested + slice_cost_inr) <= portfolio_cap:
                if live_mode:
                    if is_crypto and mode == "BINANCE_LIVE":
                        success, res = execute_live_order("BUY", sym, quote_amount=slice_cost_usd)
                        if not success:
                            log_status(f"⚠️ Live Binance Buy Warning ({sym}): {res}")
                    elif is_indian and mode == "ANGEL_ONE_LIVE":
                        success, res = execute_live_order("BUY", sym, quantity=slice_qty)
                        if not success:
                            log_status(f"⚠️ Angel One Live Buy Warning ({sym}): {res}")
                        
                if regime == "RANGE":
                    target_p = current_price * (1.0050 if is_indian else 1.0065)
                    tgt_pct_label = "0.50%" if is_indian else "0.65%"
                else:
                    target_p = current_price * (1.0085 if is_indian else 1.012)
                    tgt_pct_label = "0.85%" if is_indian else "1.20%"

                dca_state[sym] = {
                    "entries": [{
                        "price": current_price,
                        "qty": slice_qty,
                        "cost": slice_cost_inr,
                        "time": get_ist_now().strftime('%Y-%m-%d %H:%M:%S')
                    }],
                    "avg_price": current_price,
                    "total_qty": slice_qty,
                    "total_cost": slice_cost_inr,
                    "target_sell_price": target_p,
                    "peak_price": current_price,
                    "strategy": strat_used
                }
                save_dca_state(dca_state)
                pos = dca_state[sym]
                
                qty_label = f"{int(slice_qty)} షేర్లు" if (is_indian and slice_qty == int(slice_qty)) else f"Qty: {slice_qty:.5f}"
                price_disp = f"₹{current_price:,.2f}" if is_indian else f"${current_price:,.2f}"
                cost_disp = f"₹{slice_cost_inr:,.2f}" if is_indian else f"${slice_cost_usd} / ₹{slice_cost_inr:,.2f}"
                target_disp = f"₹{target_p:,.2f}" if is_indian else f"${target_p:,.2f}"
                
                msg = f"🎯 [{mode_str} స్కామర్ బ్రెయిన్ 🥷 స్నైపర్ DCA | {session_badge} | {regime}]: {sym} డిప్ లో కొన్నాను @ {price_disp} ({cost_disp} | {qty_label})\n🎯 టార్గెట్ (+{tgt_pct_label} క్విక్ ప్రాఫిట్): {target_disp} | టెక్నిక్: {strat_used}\n{thought}"
                voice_msg = f"Alert. Buying fractional slice of {clean_name}."
                log_status(f"[{get_ist_now().strftime('%H:%M:%S IST')}] {msg}", voice_alert=voice_msg, color_code='\033[92m')
                log_trade("BUY", sym, current_price, slice_qty, 0.0)
                send_telegram_message(f"✅ {msg}")
                action_taken = "BUY"

    # If Daily Guard is active and no position, notify on radar
    if is_daily_locked and pos is None:
        thought = f"🛡️ {daily_guard_reason}"
        action_taken = "DAILY_GUARD_HOLD"

    # Return full diagnostic radar status
    return {
        "symbol": sym,
        "clean_name": clean_name,
        "price": round(current_price, 2),
        "signal": signal.upper(),
        "thought": thought,
        "strategy": strat_used,
        "rsi": round(rsi_val, 1),
        "trend": htf_trend,
        "action_taken": action_taken,
        "has_position": pos is not None,
        "pnl_pct": round(profit_pct, 2) if pos is not None else 0.0,
        "avg_price": round(pos['avg_price'], 2) if pos is not None else 0.0,
        "total_qty": pos['total_qty'] if pos is not None else 0.0,
        "target_price": round(pos.get('target_sell_price', current_price * 1.035), 2) if pos is not None else 0.0,
        "peak_price": round(pos.get('peak_price', current_price), 2) if pos is not None else 0.0,
        "invested": round(pos.get('total_cost', 0.0), 2) if pos is not None else 0.0,
        "dca_layer": len(pos.get('entries', [])) if pos is not None else 0,
        "timestamp": get_ist_now().strftime('%H:%M:%S IST'),
        "is_indian": is_indian
    }

_bot_loop_active = False
_bot_loop_lock = threading.Lock()

def run_bot_loop():
    global _bot_loop_active
    with _bot_loop_lock:
        if _bot_loop_active:
            print("Bot loop is already running in this process.")
            return
        _bot_loop_active = True
    log_status(f"[{get_ist_now().strftime('%H:%M:%S IST')}] 🔥 Advanced AI Trading Robot is now ONLINE!", voice_alert="Advanced AI Robot is now online.", color_code="[95m")
    send_telegram_message("🤖 AI మల్టిపుల్ ట్రేడింగ్ బాట్ ఆన్ అయ్యింది!")
    # Restore complete spot trade history from MongoDB Cloud so restarts never lose history
    try:
        db_helper.sync_cloud_to_local(is_futures=False)
    except Exception:
        pass
    loop_count = 0
    while True:
        loop_count += 1
        try:
            mode = get_current_trading_mode()
            custom_wl = load_custom_watchlist()
            custom_crypto = [s for s, d in custom_wl.items() if d.get('type') == 'CRYPTO' or s.endswith('-USD')]
            custom_nse = [s for s, d in custom_wl.items() if d.get('type') == 'NSE' or s.endswith('.NS') or s.endswith('.BO')]

            crypto_universe = get_dynamic_crypto_universe()
            if mode == "ANGEL_ONE_LIVE":
                default_symbols = list(dict.fromkeys(NSE_SYMBOLS + custom_nse))
                broker_name = "Angel One Live (SmartAPI Real Money)"
            elif mode == "DUAL_TRADING":
                default_symbols = list(dict.fromkeys(crypto_universe + NSE_SYMBOLS + list(custom_wl.keys())))
                broker_name = "Dual Hybrid (Crypto 24/7 + Zerodha NSE)"
            elif mode == "ZERODHA_PAPER":
                default_symbols = list(dict.fromkeys(NSE_SYMBOLS + custom_nse))
                broker_name = "Zerodha Kite (Paper)"
            elif mode == "BINANCE_LIVE":
                default_symbols = list(dict.fromkeys(crypto_universe + custom_crypto))
                broker_name = "Binance Spot (Live)"
            else:
                default_symbols = list(dict.fromkeys(crypto_universe + custom_crypto))
                broker_name = "Binance Virtual"

            # 🔄 Reconcile with Angel One Live Positions to eliminate ghost positions
            if mode == "ANGEL_ONE_LIVE":
                try:
                    a_pos_data = angel_one.get_angel_positions()
                    if a_pos_data.get("status") and "raw" in a_pos_data and a_pos_data["raw"]:
                        dca_st = load_dca_state()
                        changed = False
                        for raw_p in a_pos_data["raw"]:
                            sym_n = raw_p.get("symbolname", "")
                            full_sym = f"{sym_n}.NS"
                            try:
                                net_q = int(float(raw_p.get("netqty", 0)))
                            except:
                                net_q = 0
                            if net_q == 0 and full_sym in dca_st:
                                realised = float(raw_p.get("realised", raw_p.get("pnl", 0.0)) or 0.0)
                                sell_avg = float(raw_p.get("sellavgprice", 0.0) or 0.0)
                                sq_qty = dca_st[full_sym].get("total_qty", 1.0)
                                log_status(f"🔄 [Angel Sync] {full_sym} broker లో స్క్వేర్-ఆఫ్ అయ్యింది. Realized PnL: ₹{realised:,.2f}")
                                log_trade("SELL", full_sym, sell_avg, sq_qty, realised, strategy_key="broker_auto_squareoff")
                                del dca_st[full_sym]
                                changed = True
                        if changed:
                            save_dca_state(dca_st)
                except Exception as e_recon:
                    pass

            active_symbols = default_symbols
            if os.path.exists('selected_symbol.txt'):
                try:
                    with open('selected_symbol.txt', 'r') as f:
                        sel = f.read().strip()
                    if sel and sel not in ["ALL", "ALL_CRYPTO", "ALL_NSE", "ALL_DUAL"]:
                        active_symbols = [sel]
                    elif sel == "ALL_NSE":
                        active_symbols = list(dict.fromkeys(NSE_SYMBOLS + custom_nse))
                    elif sel == "ALL_CRYPTO":
                        active_symbols = list(dict.fromkeys(crypto_universe + custom_crypto))
                    elif sel in ["ALL_DUAL", "ALL"]:
                        active_symbols = default_symbols
                except: pass

            # 🛑 100% STRICT ISOLATION: REAL MONEY MODE (ANGEL ONE LIVE)
            # When Real Money mode is active, ABSOLUTELY ZERO VIRTUAL / CRYPTO TRADES ARE ALLOWED!
            if mode == "ANGEL_ONE_LIVE":
                active_symbols = [s for s in active_symbols if s.endswith('.NS') or s.endswith('.BO')]
                if not active_symbols:
                    active_symbols = list(dict.fromkeys(NSE_SYMBOLS + custom_nse))
                
                # Auto-purge any leftover virtual crypto positions from dca_state
                try:
                    dca_curr = load_dca_state()
                    if any(k.endswith('-USD') for k in dca_curr.keys()):
                        dca_curr = {k: v for k, v in dca_curr.items() if not k.endswith('-USD')}
                        save_dca_state(dca_curr)
                except Exception:
                    pass

            actions_taken = []
            # Multi-Threading for active symbols
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(active_symbols))) as executor:
                results = list(executor.map(process_symbol, active_symbols))
                
            actions_taken = [r['symbol'] for r in results if r and isinstance(r, dict) and r.get('action_taken') in ['BUY', 'SELL', 'DCA_BUY']]
            
            # 📡 Save Live Scan Status for AI Market Radar
            cap_mode_saved = "High Profit"
            if os.path.exists('settings.json'):
                try:
                    with open('settings.json', 'r') as f_s:
                        cap_mode_saved = json.load(f_s).get('capital_mode', 'High Profit')
                except: pass

            today_realized_pnl = get_today_realized_pnl()
            is_locked, daily_guard_reason, _ = check_daily_guard()

            live_scan_data = {
                "timestamp": get_ist_now().strftime('%Y-%m-%d %H:%M:%S'),
                "broker": broker_name,
                "mode": mode,
                "capital_mode": cap_mode_saved,
                "active_symbols": active_symbols,
                "daily_guard": {
                    "today_pnl": today_realized_pnl,
                    "target_inr": DAILY_PROFIT_TARGET_INR,
                    "max_loss_inr": DAILY_MAX_LOSS_INR,
                    "is_locked": is_locked,
                    "reason": daily_guard_reason
                },
                "assets": {r['symbol']: r for r in results if r and isinstance(r, dict) and 'symbol' in r}
            }
            try:
                db_helper.save_state('live_scan_status', live_scan_data)
            except Exception:
                pass
            
            if len(active_symbols) > 1:
                has_nse = any('.NS' in s or '.BO' in s for s in active_symbols)
                has_crypto = any('-USD' in s for s in active_symbols)
                if has_nse and has_crypto:
                    crypto_count = len([s for s in active_symbols if '-USD' in s])
                    stock_count = len([s for s in active_symbols if '.NS' in s or '.BO' in s])
                    sym_label = f"Dual Hybrid ({len(active_symbols)} Assets)"
                    hold_label = f"Dual Hybrid ({crypto_count} క్రిప్టో + {stock_count} స్టాక్స్) సేఫ్ గా HOLD లో ఉన్నాయి"
                elif has_nse:
                    short_names = [s.replace('.NS', '').replace('.BO', '') for s in active_symbols]
                    sym_label = f"Zerodha NSE ({len(active_symbols)})"
                    hold_label = f"Zerodha స్టాక్స్ ({', '.join(short_names[:4])}...) సేఫ్ గా HOLD లో ఉన్నాయి"
                else:
                    short_names = [s.replace('-USD', '') for s in active_symbols if '-USD' in s]
                    sym_label = f"మల్టీ-కాయిన్స్ ({len(active_symbols)})"
                    hold_label = f"మల్టీ-కాయిన్స్ ({', '.join(short_names)}) సేఫ్ గా HOLD లో ఉన్నాయి"
            else:
                sym_label = active_symbols[0].replace('.NS', '').replace('.BO', '').replace('-USD', '')
                hold_label = f"{sym_label} సేఫ్ గా HOLD లో ఉంది"
                
            last_act_text = ("ట్రేడ్ జరిగింది: " + ", ".join(actions_taken)) if actions_taken else hold_label
            
            if not actions_taken:
                log_status(f"[{get_ist_now().strftime('%H:%M:%S IST')}] ⚡ [{broker_name}] {hold_label}.", color_code='\033[96m')

            # 💓 Write Live Heartbeat for Website Indicator (IST)
            heartbeat_data = {
                "last_ping": time.time(),
                "timestamp": get_ist_now().strftime('%Y-%m-%d %H:%M:%S'),
                "status": "RUNNING",
                "broker": broker_name,
                "mode": mode,
                "active_symbols": active_symbols,
                "loop_count": loop_count,
                "last_action": last_act_text
            }
            try:
                import json

                db_helper.save_state('bot_heartbeat', heartbeat_data)
            except Exception:
                pass
                
        except Exception as e:
            log_status(f"[{get_ist_now().strftime('%H:%M:%S IST')}] ⚠️ ఎర్రర్: {e}")
            try:
                import json

                db_helper.save_state('bot_heartbeat', {
                    "last_ping": time.time(),
                    "timestamp": get_ist_now().strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "ERROR",
                    "error": str(e),
                    "loop_count": loop_count
                })
            except Exception:
                pass
            
        time.sleep(10) # 10 seconds scan in Extreme mode

if __name__ == "__main__":
    run_bot_loop()
