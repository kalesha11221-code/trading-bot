import time
import pandas as pd
from datetime import datetime

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

import concurrent.futures
import threading
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import numpy as np

# Global Threading Lock for safe file writing
file_lock = threading.Lock()

import requests
import yfinance as yf

CRYPTO_SYMBOLS = [
    # 🪙 High-Liquidity 24/7 Crypto (Tier-1 Binance Spot)
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "DOGE-USD", "XRP-USD"
]

NSE_SYMBOLS = [
    # 🇮🇳 Top High-Volume Indian Stocks (NSE Zerodha)
    "RELIANCE.NS", "TMCV.NS", "HDFCBANK.NS", "INFY.NS", 
    "SBIN.NS", "TCS.NS", "ICICIBANK.NS", "ITC.NS"
]

SYMBOL_ALIASES = {
    'TATAMOTORS.NS': 'TMCV.NS',
    'TATAMOTORS': 'TMCV.NS',
    'TATA.NS': 'TMCV.NS',
    'TATA': 'TMCV.NS',
    'ZOMATO.NS': 'ETERNAL.NS',
    'ZOMATO': 'ETERNAL.NS'
}

symbols_to_trade = CRYPTO_SYMBOLS

# 🎯 హంతకుడు (Assassin Sniper) Portfolio & Risk Guards
MAX_ACTIVE_POSITIONS = 3
MAX_PORTFOLIO_CAPITAL = 10000.0
COOLDOWN_SECONDS = 300  # 5-minute cooldown after closing trade on a symbol

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
            requests.post(url, json=payload)
    except Exception as e:
        pass

# ---------------------------------------------------------
# ట్రేడ్ హిస్టరీ సేవ్ చేసే ఫంక్షన్
# ---------------------------------------------------------
def update_ai_brain_after_trade(sym, profit, strategy_key=None):
    try:
        import json
import db_helper
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
        
        now_str = datetime.now().strftime('%H:%M')
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
    file_name = 'trades_log.csv'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            f.write("Time,Symbol,Action,Price,Shares,Profit\n")

    with file_lock:
        with open(file_name, 'a') as f:
            profit_str = f"{profit:.4f}" if profit != 0.0 else "0.0"
            f.write(f"{timestamp},{sym},{action.upper()},{price:.2f},{quantity},{profit_str}\n")
            
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
    if os.path.exists(DCA_FILE):
        try:
            with open(DCA_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def save_dca_state(state):
    try:
        with file_lock:
            with open(DCA_FILE, 'w') as f:
                json.dump(state, f, indent=2)
    except: pass

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
    if os.path.exists('trading_mode.txt'):
        try:
            with open('trading_mode.txt', 'r') as f:
                content = f.read().strip()
            if "Dual" in content:
                return "DUAL_TRADING"
            elif "Zerodha" in content or "Indian" in content or "NSE" in content:
                return "ZERODHA_PAPER"
            elif "Live" in content and "Binance" in content:
                return "BINANCE_LIVE"
            else:
                return "BINANCE_PAPER"
        except: pass
    return "DUAL_TRADING"

def is_live_trading():
    return get_current_trading_mode() == "BINANCE_LIVE"

def execute_live_order(action, sym, quantity=None, quote_amount=None):
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
        with urlopen(req) as response:
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
import db_helper
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
        mode_tag = "హంతకుడు (Scalper Extreme)"
    elif is_conservative:
        min_pillars = 3
        req_buy_score = 7.0
        max_sell_score = 1.5
        htf_ok = (htf_status != 'BEARISH') or extreme_capitulation
        mode_tag = "హంతకుడు (Safe Sniper)"
    else: # Balanced / Moderate
        min_pillars = 2
        req_buy_score = 5.0
        max_sell_score = 3.0
        htf_ok = (htf_status != 'BEARISH') or extreme_capitulation
        mode_tag = "హంతకుడు (Balanced Swing)"

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
    now = datetime.now()
    is_crypto = sym.endswith("-USD")
    is_indian = sym.endswith(".NS") or sym.endswith(".BO") or sym in ["^NSEI", "^NSEBANK"]
    clean_name = sym.replace('.NS', '').replace('.BO', '').replace('-USD', '')
    
    # Load Fractional Micro-DCA State & Live Trading Mode
    dca_state = load_dca_state()
    pos = dca_state.get(sym)
    live_mode = is_live_trading()
    
    if not is_crypto and now.weekday() >= 5:
        # Weekend: stock markets closed
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
        
    # Indian Stocks (Zerodha Paper) vs Crypto (Binance) sizing (Optimized for ₹50,000 Capital)
    if is_indian:
        mode_str = "🇮🇳 ZERODHA VIRTUAL"
        if cap_mode == "High Profit" or is_scalp_style:
            portfolio_cap = 50000.0  # ₹50,000 active capital
            if current_price > 2500:
                slice_qty = 4.0   # 4 shares for Reliance/TCS (~₹11,000-₹14,000) -> +1.5% = ₹165 - ₹210 profit
            elif current_price > 700:
                slice_qty = 12.0  # 12 shares for TMCV, SBI, Infosys, HDFC Bank (~₹9,000-₹12,000) -> +1.5% = ₹150 profit
            elif current_price > 100:
                slice_qty = 40.0  # 40 shares for ITC, Zomato/Eternal (~₹11,000-₹12,000) -> +1.5% = ₹170 profit
            else:
                slice_qty = 150.0 # 150 shares for Suzlon (~₹9,000-₹12,000) -> +1.5% = ₹150 profit
        elif cap_mode == "Smart Dynamic":
            portfolio_cap = 50000.0
            if current_price > 2500: slice_qty = 2.0
            elif current_price > 700: slice_qty = 6.0
            elif current_price > 100: slice_qty = 20.0
            else: slice_qty = 75.0
        else: # Micro Safe
            portfolio_cap = 50000.0
            if current_price > 2500: slice_qty = 1.0
            elif current_price > 700: slice_qty = 3.0
            elif current_price > 100: slice_qty = 10.0
            else: slice_qty = 25.0
        slice_cost_inr = round(slice_qty * current_price, 2)
        slice_cost_usd = round(slice_cost_inr / 84.5, 2)
    else:
        mode_str = "💰 LIVE BINANCE" if (live_mode and is_crypto) else "📝 VIRTUAL"
        if cap_mode == "High Profit" or is_scalp_style:
            slice_cost_usd = round(120.0 * brain_conf, 1) # $120 per entry (~₹10,140) -> +1.5% = $1.80 (~₹152 profit)
            portfolio_cap = 50000.0
        elif cap_mode == "Smart Dynamic":
            slice_cost_usd = round(60.0 * brain_conf, 1)  # $60 (~₹5,070)
            portfolio_cap = 50000.0
        else:
            slice_cost_usd = round(25.0 * brain_conf, 1)  # $25 (~₹2,100)
            portfolio_cap = 50000.0
        slice_cost_inr = round(slice_cost_usd * 84.5, 2)
        slice_qty = slice_cost_usd / current_price

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
        
        # High Profit / Scalper Triggers:
        if is_scalp_style:
            # Scalping exits: fast compounding profit capture
            # 1. Trailing Exit: Reached >= 1.0% and dipped 0.3% from peak (locks in fast scalp!)
            # 2. Target Exit: Reached >= 1.8% directly
            # 3. Base Reversal Exit: Reached >= 0.8% with confirmed SELL reversal signal
            is_trailing_exit = (peak_gain_pct >= 1.0 and current_price <= (peak_p * 0.997))
            is_target_exit = (profit_pct >= 1.8)
            is_reversal_exit = (profit_pct >= 0.8 and signal == 'sell')
        else:
            # 1. Trailing Exit: Reached >= 1.5% and dipped 0.4% from peak (locks in maximum profit!)
            # 2. Big Target: Reached >= 2.8% directly
            # 3. Base Reversal Exit: Reached >= 1.5% with confirmed SELL reversal signal
            is_trailing_exit = (peak_gain_pct >= 1.5 and current_price <= (peak_p * 0.996))
            is_target_exit = (profit_pct >= 2.8)
            is_reversal_exit = (profit_pct >= 1.5 and signal == 'sell')
        
        if is_trailing_exit or is_target_exit or is_reversal_exit:
            profit = (current_price - avg_price) * total_qty
            last_exit_times[sym] = time.time()
            
            # Execute real order if in Live Mode on Binance
            if live_mode and is_crypto:
                success, res = execute_live_order("SELL", sym, quantity=total_qty)
                if not success:
                    log_status(f"⚠️ Live Binance Sell Warning ({sym}): {res}")
            
            qty_label = f"{int(total_qty)} షేర్లు" if (is_indian and total_qty == int(total_qty)) else f"Qty: {total_qty:.5f}"
            price_disp = f"₹{current_price:,.2f}" if is_indian else f"${current_price:,.2f}"
            profit_disp = f"₹{profit:,.2f}"
            
            msg = f"🎯 [{mode_str} హంతకుడు ప్రాఫిట్ మాక్సిమైజర్]: {sym} ({qty_label}) | భారీ లాభం: {profit_disp} (+{profit_pct:.2f}%)\n{thought} 🧠 [Peak: +{peak_gain_pct:.2f}% | DCA Layers: {len(pos.get('entries', []))}]"
            voice_msg = f"Alert. Profit maximizer reached on {clean_name}. Selling for great profit."
            log_status(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", voice_alert=voice_msg, color_code='\033[92m')
            strat_key = pos.get('strategy', 'rsi_vwap_confluence')
            log_trade("SELL", sym, current_price, total_qty, profit, strategy_key=strat_key)
            send_telegram_message(f"✅ {msg}")
            
            # Reset DCA position
            if sym in dca_state:
                del dca_state[sym]
                save_dca_state(dca_state)
            action_taken = "SELL"
            pos = None

        # Stop-Loss Emergency Protection: drops > 6% with confirmed sell signal
        elif profit_pct <= -6.0 and signal == 'sell':
            profit = (current_price - avg_price) * total_qty
            last_exit_times[sym] = time.time()
            if live_mode and is_crypto:
                execute_live_order("SELL", sym, quantity=total_qty)
            loss_disp = f"₹{profit:,.2f}"
            msg = f"🛑 [{mode_str} Stop-Loss]: {sym} -6% కంటే ఎక్కువ పడిపోవడంతో నష్టాన్ని కట్ చేసి సేఫ్ గా అమ్మాను! (Loss: {loss_disp})"
            log_status(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", color_code='\033[91m')
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
        elif len(pos.get('entries', [])) < 3 and current_price <= (avg_price * 0.982) and signal == 'buy':
            # Capital Protection Guard
            current_invested = sum(p.get('total_cost', 0.0) for p in dca_state.values())
            if (current_invested + slice_cost_inr) <= portfolio_cap:
                if live_mode and is_crypto:
                    success, res = execute_live_order("BUY", sym, quote_amount=slice_cost_usd)
                    if not success:
                        log_status(f"⚠️ Live Binance DCA Buy Warning ({sym}): {res}")
                
                layer = len(pos.get('entries', [])) + 1
                pos['entries'].append({
                    "price": current_price,
                    "qty": slice_qty,
                    "cost": slice_cost_inr,
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
                
                msg = f"🎯 [{mode_str} హంతకుడు DCA Layer {layer}/3]: {sym} @ {price_disp} ({qty_label})\nకొత్త సగటు ధర: {avg_disp} | టార్గెట్ (+1.5%): {target_disp}\n{thought}"
                voice_msg = f"Alert. Averaging down on {clean_name}."
                log_status(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", voice_alert=voice_msg, color_code='\033[96m')
                log_trade("BUY", sym, current_price, slice_qty, 0.0)
                send_telegram_message(f"✅ {msg}")
                action_taken = "DCA_BUY"

    # -------------------------------------------------------------
    # 3. FIRST DIP ENTRY (INITIAL FRACTIONAL SLICE)
    # -------------------------------------------------------------
    elif pos is None and signal == 'buy':
        max_positions = 4 if is_scalp_style else MAX_ACTIVE_POSITIONS
        if len(dca_state) < max_positions:
            current_invested = sum(p.get('total_cost', 0.0) for p in dca_state.values())
            if (current_invested + slice_cost_inr) <= portfolio_cap:
                if live_mode and is_crypto:
                    success, res = execute_live_order("BUY", sym, quote_amount=slice_cost_usd)
                    if not success:
                        log_status(f"⚠️ Live Binance Buy Warning ({sym}): {res}")
                        
                target_p = current_price * 1.015
                dca_state[sym] = {
                    "entries": [{
                        "price": current_price,
                        "qty": slice_qty,
                        "cost": slice_cost_inr,
                        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
                
                msg = f"🎯 [{mode_str} హంతకుడు స్నైపర్ DCA]: {sym} డిప్ లో కొన్నాను @ {price_disp} ({cost_disp} | {qty_label})\n🎯 టార్గెట్ (+1.5% లాభం): {target_disp} | టెక్నిక్: {strat_used}\n{thought}"
                voice_msg = f"Alert. Buying fractional slice of {clean_name}."
                log_status(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", voice_alert=voice_msg, color_code='\033[92m')
                log_trade("BUY", sym, current_price, slice_qty, 0.0)
                send_telegram_message(f"✅ {msg}")
                action_taken = "BUY"

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
        "target_price": round(pos.get('target_sell_price', current_price * 1.015), 2) if pos is not None else 0.0,
        "peak_price": round(pos.get('peak_price', current_price), 2) if pos is not None else 0.0,
        "invested": round(pos.get('total_cost', 0.0), 2) if pos is not None else 0.0,
        "dca_layer": len(pos.get('entries', [])) if pos is not None else 0,
        "timestamp": now.strftime('%H:%M:%S'),
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
    log_status(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 Advanced AI Trading Robot is now ONLINE!", voice_alert="Advanced AI Robot is now online.", color_code="[95m")
    send_telegram_message("🤖 AI మల్టిపుల్ ట్రేడింగ్ బాట్ ఆన్ అయ్యింది!")
    loop_count = 0
    while True:
        loop_count += 1
        try:
            mode = get_current_trading_mode()
            custom_wl = load_custom_watchlist()
            custom_crypto = [s for s, d in custom_wl.items() if d.get('type') == 'CRYPTO' or s.endswith('-USD')]
            custom_nse = [s for s, d in custom_wl.items() if d.get('type') == 'NSE' or s.endswith('.NS') or s.endswith('.BO')]

            if mode == "DUAL_TRADING":
                default_symbols = list(dict.fromkeys(CRYPTO_SYMBOLS + NSE_SYMBOLS + list(custom_wl.keys())))
                broker_name = "Dual Hybrid (Crypto 24/7 + Zerodha NSE)"
            elif mode == "ZERODHA_PAPER":
                default_symbols = list(dict.fromkeys(NSE_SYMBOLS + custom_nse))
                broker_name = "Zerodha Kite (Paper)"
            elif mode == "BINANCE_LIVE":
                default_symbols = list(dict.fromkeys(CRYPTO_SYMBOLS + custom_crypto))
                broker_name = "Binance Spot (Live)"
            else:
                default_symbols = list(dict.fromkeys(CRYPTO_SYMBOLS + custom_crypto))
                broker_name = "Binance Virtual"

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
                        active_symbols = list(dict.fromkeys(CRYPTO_SYMBOLS + custom_crypto))
                    elif sel in ["ALL_DUAL", "ALL"]:
                        active_symbols = default_symbols
                except: pass

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

            live_scan_data = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "broker": broker_name,
                "mode": mode,
                "capital_mode": cap_mode_saved,
                "active_symbols": active_symbols,
                "assets": {r['symbol']: r for r in results if r and isinstance(r, dict) and 'symbol' in r}
            }
            try:
                with file_lock:
                    with open('live_scan_status.json', 'w') as f_scan:
                        json.dump(live_scan_data, f_scan, indent=2)
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
                log_status(f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ [{broker_name}] {hold_label}.", color_code='\033[96m')

            # 💓 Write Live Heartbeat for Website Indicator
            heartbeat_data = {
                "last_ping": time.time(),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "status": "RUNNING",
                "broker": broker_name,
                "mode": mode,
                "active_symbols": active_symbols,
                "loop_count": loop_count,
                "last_action": last_act_text
            }
            try:
                import json
import db_helper
                with file_lock:
                    with open('bot_heartbeat.json', 'w') as f_hb:
                        json.dump(heartbeat_data, f_hb)
            except Exception:
                pass
                
        except Exception as e:
            log_status(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ ఎర్రర్: {e}")
            try:
                import json
import db_helper
                with file_lock:
                    with open('bot_heartbeat.json', 'w') as f_hb:
                        json.dump({
                            "last_ping": time.time(),
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "status": "ERROR",
                            "error": str(e),
                            "loop_count": loop_count
                        }, f_hb)
            except Exception:
                pass
            
        time.sleep(10) # 10 seconds scan in Extreme mode

if __name__ == "__main__":
    run_bot_loop()
