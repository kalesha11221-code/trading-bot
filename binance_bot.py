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

symbols_to_trade = [
    # 🪙 Crypto (24/7)
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
    # 🇮🇳 Indian Stocks & Indices
    "^NSEI", "^NSEBANK", "RELIANCE.NS", "INFY.NS", "SBIN.NS",
    # 🇺🇸 US Stocks
    "AAPL", "TSLA", "NVDA", "AMZN",
    # 💱 Forex (Currencies)
    "EURUSD=X", "GBPUSD=X", "JPY=X",
    # 🛢️ Commodities
    "GLD", # Gold
    "USO"  # Crude Oil
]

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
def log_trade(action, sym, price, quantity, profit=0.0):
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
        import json
        try:
            try:
                with open('ai_brain.json', 'r') as f:
                    brain = json.load(f)
            except:
                brain = {"RSI_weight": 1.0, "MACD_weight": 1.0, "BOL_weight": 1.0, "ML_weight": 1.0, "learning_iterations": 0}
            
            brain['learning_iterations'] += 1
            if profit > 0:
                # Trade succeeded: Trust the current setup more
                brain['MACD_weight'] = min(2.0, brain['MACD_weight'] + 0.02)
                brain['ML_weight'] = min(2.0, brain['ML_weight'] + 0.03)
            else:
                # Trade failed: Market is tricky, rely more on Volatility (Bollinger) and RSI bounds
                brain['BOL_weight'] = min(2.0, brain['BOL_weight'] + 0.05)
                brain['RSI_weight'] = min(2.0, brain['RSI_weight'] + 0.02)
                # Punish the trend indicators slightly
                brain['MACD_weight'] = max(0.5, brain['MACD_weight'] - 0.02)
                brain['ML_weight'] = max(0.5, brain['ML_weight'] - 0.03)
                
            with open('ai_brain.json', 'w') as f:
                json.dump(brain, f)
        except Exception as e:
            pass


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
    })
except:
    pass

def execute_live_order(action, sym, quantity):
    if not exchange: return False
    # CCXT expects symbol like BTC/USDT. We have BTC-USD.
    market_sym = sym.replace("-USD", "/USDT")
    try:
        if action == "BUY":
            exchange.create_market_buy_order(market_sym, quantity)
        elif action == "SELL":
            exchange.create_market_sell_order(market_sym, quantity)
        return True
    except Exception as e:
        log_status(f"⚠️ Live Order Error: {e}")
        return False



# Cache for Macro Trends to avoid downloading 2-year data every minute
macro_trends = {}

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
    with yf_lock:
        df = yf.download(sym, period="7d", interval="1m", progress=False)
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
    
    # Anti-Corruption check
    if 'close' in df.columns and isinstance(df['close'], pd.DataFrame):
        return pd.DataFrame() 
    return df

import numpy as np
    

def get_news_sentiment(sym):
    try:
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


def generate_signal(df, sym):
    # 🧠 SELF-LEARNING AI BRAIN
    import json
    try:
        with open('ai_brain.json', 'r') as f:
            ai_brain = json.load(f)
    except:
        ai_brain = {"RSI_weight": 1.0, "MACD_weight": 1.0, "BOL_weight": 1.0, "ML_weight": 1.0, "learning_iterations": 0}

    current_price = df.iloc[-1]['close']
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # సపోర్ట్ అండ్ రెసిస్టెన్స్
    df['Support'] = df['low'].rolling(window=200).min()
    df['Resistance'] = df['high'].rolling(window=200).max()
    
    # బోలింజర్ బ్యాండ్స్ (Bollinger Bands - Volatility కొలవడానికి)
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['STD_20'] = df['close'].rolling(window=20).std()
    df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    # ATR (Average True Range) - ఎంత స్పీడ్ గా కదులుతుందో చూసి స్టాప్ లాస్ డిసైడ్ చేయడానికి
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    # VWAP (Volume Weighted Average Price) - ప్రో ట్రేడర్స్ వాడే అడ్వాన్స్డ్ ఇండికేటర్
    df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
    # సాధారణంగా VWAP రోజువారీ (Daily) క్యాలిక్యులేట్ చేస్తారు, కానీ మనం ఇక్కడ రీసెంట్ 50 క్యాండిల్స్ తీసుకుందాం
    df['VWAP'] = (df['Typical_Price'] * df['volume']).rolling(window=50).sum() / df['volume'].rolling(window=50).sum()
    
    # వాల్యూమ్ అనాలసిస్ (Big players ఎంటర్ అయ్యారా అని చూడటానికి)
    avg_volume = df['volume'].rolling(window=20).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_Line'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    
    
    # Advanced Sniper Indicator: ADX (Trend Strength)
    df['+DM'] = df['high'].diff()
    df['-DM'] = -df['low'].diff()
    df['+DM'] = np.where((df['+DM'] > df['-DM']) & (df['+DM'] > 0), df['+DM'], 0.0)
    df['-DM'] = np.where((df['-DM'] > df['+DM']) & (df['-DM'] > 0), df['-DM'], 0.0)
    
    df['TR'] = np.maximum((df['high'] - df['low']), np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    
    # Smooth them over 14 periods (using simple rolling mean for speed instead of Wilder's)
    df['+DI'] = 100 * (df['+DM'].rolling(14).mean() / df['TR'].rolling(14).mean())
    df['-DI'] = 100 * (df['-DM'].rolling(14).mean() / df['TR'].rolling(14).mean())
    df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])
    df['ADX'] = df['DX'].rolling(14).mean()
    df.fillna(0, inplace=True)

    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    near_support = last['close'] <= (last['Support'] * 1.002)
    near_resistance = last['close'] >= (last['Resistance'] * 0.998)
    volume_spike = last['volume'] > (avg_volume.iloc[-1] * 2) if not pd.isna(avg_volume.iloc[-1]) else False
    
    # అడ్వాన్స్డ్ AI థింకింగ్ ప్రాసెస్ (Pro Scoring System)
    buy_score = 0
    sell_score = 0
    thoughts = []
    
    if last['close'] > last['EMA_200']:
        buy_score += 1
        thoughts.append("ట్రెండ్ పాజిటివ్ గా ఉంది.")
    else:
        sell_score += 1
        thoughts.append("ట్రెండ్ నెగెటివ్ గా ఉంది.")
        
    if not pd.isna(last['VWAP']):
        if last['close'] > last['VWAP']:
            buy_score += 1
            thoughts.append("ప్రైస్ VWAP లైన్ కి పైన ఉంది (ప్రో ట్రేడర్స్ కొంటున్నారు).")
        else:
            sell_score += 1
            thoughts.append("ప్రైస్ VWAP లైన్ కి కింద ఉంది (మార్కెట్ వీక్ గా ఉంది).")
        
    if last['RSI'] < 35:
        buy_score += 2
        thoughts.append("RSI బాగా పడిపోయి ఓవర్-సోల్డ్ కి వచ్చింది (కొనడానికి బెస్ట్ టైమ్).")
    elif last['RSI'] > 70:
        sell_score += 2
        thoughts.append("RSI బాగా పెరిగిపోయి ఓవర్-బాట్ కి వెళ్ళింది (అమ్మడానికి టైమ్).")
        
    if last['close'] <= last['Lower_Band']:
        buy_score += 2
        thoughts.append("ప్రైస్ బోలింజర్ బ్యాండ్ అడుగు భాగాన్ని తాకింది (ఇక్కడి నుంచి పక్కాగా బౌన్స్ అవుతుంది).")
    elif last['close'] >= last['Upper_Band']:
        sell_score += 2
        thoughts.append("ప్రైస్ బోలింజర్ బ్యాండ్ పై భాగాన్ని దాటేసింది (విపరీతంగా పెరిగింది, పడిపోవచ్చు).")
        
    if prev['MACD_Line'] <= prev['MACD_Signal'] and last['MACD_Line'] > last['MACD_Signal']:
        buy_score += 2
        thoughts.append("MACD బులెట్ లాగా పైకి క్రాస్ అయ్యింది.")
    elif prev['MACD_Line'] >= prev['MACD_Signal'] and last['MACD_Line'] < last['MACD_Signal']:
        sell_score += 2
        thoughts.append("MACD కిందకి క్రాస్ అయ్యింది.")
        
    if near_support:
        buy_score += 2
        thoughts.append("పాత హిస్టరీ ప్రకారం ఇక్కడే సపోర్ట్ తీసుకుంది.")
    if near_resistance:
        sell_score += 2
        thoughts.append("హిస్టరీ ప్రకారం ఇది రెసిస్టెన్స్ ఏరియా.")
        
    if volume_spike:
        thoughts.append("సడెన్ గా మార్కెట్ లోకి పెద్ద ప్లేయర్స్ (వాల్యూమ్) వచ్చారు!")
        if last['close'] > prev['close']:
            buy_score += 1
        else:
            sell_score += 1
            
    # డెసిషన్ మేకింగ్ (Super Fast Scalping Mode - కేవలం 2 పాయింట్లు వచ్చినా ట్రేడ్ చేస్తుంది)

        
    
    # 🦸‍♂️ SUPER-HERO FEATURE 1: WHALE RADAR (Volume Anomaly Detection)
    vol_mean = df['volume'].tail(15).mean()
    vol_current = df['volume'].iloc[-1]
    is_whale_pump = False
    if vol_current > vol_mean * 4: # 400% volume spike
        buy_score += 3
        is_whale_pump = True
        thoughts.append("🐋 [WHALE RADAR]: సడెన్ గా వేల్స్ (పెద్ద ప్లేయర్స్) భారీగా కొంటున్నారు! నేను కూడా వాళ్ళతో పాటు జాయిన్ అవుతున్నాను!")

    # 🛡️ SUPER-HERO FEATURE 2: FLASH CRASH PROTECTOR
    price_drop_1m = (df['close'].iloc[-2] - current_price) / df['close'].iloc[-2] * 100
    if price_drop_1m > 1.5: # 1.5% drop in 1 minute is a crash
        sell_score += 5
        thoughts.append("🛑 [FLASH CRASH SHIELD]: మార్కెట్ సడెన్ గా క్రాష్ అవుతోంది! వెంటనే షీల్డ్ ఆన్ చేసి అన్నీ అమ్మేస్తున్నాను!")

    # 🤖 SUPER-HERO FEATURE 3: AUTO-RECOVERY MODE
    total_t, w = get_symbol_performance(sym)
    win_rate = (w / total_t) if total_t > 0 else 0.50
    # If win_rate is extremely poor (< 30%), it forces itself into safe mode
    if total_t > 2 and win_rate < 0.30:
        thoughts.append("⚠️ [AUTO-RECOVERY]: మార్కెట్ చాలా దారుణంగా ఉంది. నేను పూర్తి డిఫెన్స్ మోడ్ (Safe Mode) లోకి వెళుతున్నాను.")
        if buy_score > 0: buy_score -= 2 # Extremely hard to buy

    # --- EXTREME FEATURE 2 & 3: ML Predictor & Sentiment ---
    try:
        # Machine Learning: Simple Linear Regression on last 20 periods
        x = np.arange(20)
        y = df['close'].tail(20).values
        slope, intercept = np.polyfit(x, y, 1)
        predicted_next = slope * 20 + intercept
        
        if slope > 0 and predicted_next > current_price * 1.001:
            buy_score += (2 * ai_brain.get('ML_weight', 1.0))
            thoughts.append(f"[ML Bot]: నా AI మ్యాథ్స్ ప్రకారం ప్రైస్ ₹{predicted_next:.2f} కి వెళుతుంది!")
        elif slope < 0 and predicted_next < current_price * 0.999:
            sell_score += 2
            thoughts.append(f"[ML Bot]: నా AI మ్యాథ్స్ ప్రకారం ప్రైస్ ₹{predicted_next:.2f} కి పడిపోతుంది!")
            
        # Sentiment Analysis
        news_score = get_news_sentiment(sym)
        if news_score >= 2:
            buy_score += 2
            thoughts.append(f"[News Scanner]: ఇంటర్నెట్ లో పాజిటివ్ న్యూస్ ట్రెండ్ అవుతోంది!")
        elif news_score <= -2:
            sell_score += 2
            thoughts.append(f"[News Scanner]: ఇంటర్నెట్ లో నెగెటివ్ న్యూస్ ట్రెండ్ అవుతోంది (డేంజర్)!")
    except Exception as e:
        pass
    # --------------------------------------------------------

    
    # --- CHATBOT COMMAND LISTENER ---
    import os
    if os.path.exists('ai_commands.txt'):
        try:
            with open('ai_commands.txt', 'r') as f:
                cmd = f.read().strip()
            if cmd:
                if cmd == "PANIC_SELL_ALL":
                    open('ai_commands.txt', 'w').close()
                elif cmd.startswith("FORCE_BUY"):
                    coin = cmd.split(" ")[1]
                    if sym == coin:
                        thoughts.append(f"🤖 [CHATBOT COMMAND]: బాస్ నన్ను డైరెక్ట్ గా {coin} కొనమన్నారు! సిగ్నల్ తో పనిలేదు, వెంటనే కొంటున్నాను!")
                        buy_score += 100 # Force it to buy immediately
                        open('ai_commands.txt', 'w').close() # clear it
        except:
            pass

    if buy_score >= 4: # Increased threshold because of new features
        return 'buy', f" 🧠 AI ఆలోచన (Scalper): " + " ".join(thoughts) + f" (Volatility: {last['ATR']:.2f}) ఫాస్ట్ సిగ్నల్ వచ్చింది కాబట్టి BUY చేస్తున్నాను!"
    elif sell_score >= 2:
        return 'sell', f" 🧠 AI ఆలోచన (Scalper): " + " ".join(thoughts) + f" (Volatility: {last['ATR']:.2f}) రిస్క్ ఉంది కాబట్టి వెంటనే SELL చేస్తున్నాను!"
    
    return 'hold', " 🧠 AI ఆలోచన (Pro): " + " ".join(thoughts) + " సరైన కన్ఫర్మేషన్ లేదు, కాబట్టి వెయిట్ చేస్తున్నాను."

def log_status(msg, voice_alert=None, color_code='\033[0m'):
    print(f"{color_code}{msg}\033[0m")
    with file_lock:
        with open('bot_logs.txt', 'a') as f:
            f.write(msg + '\n')
    if voice_alert:
        # Mac OS Voice Command is muted as per user request
        pass # os.system(f'say "{voice_alert}" &')

log_status(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 Advanced AI Trading Robot is now ONLINE!", voice_alert="Advanced AI Robot is now online.", color_code='\033[95m')
send_telegram_message("🤖 AI మల్టిపుల్ ట్రేడింగ్ బాట్ ఆన్ అయ్యింది!")


def process_symbol(sym):
    now = datetime.now()
    if not sym.endswith("-USD") and now.weekday() >= 5:
        return None
        
    df = fetch_data(sym)
    if df.empty:
        return None
        
    signal, thought = generate_signal(df, sym)
    current_price = df.iloc[-1]['close']
    current_pos = get_current_position(sym)
    
    if signal == 'buy' and current_pos != 'BUY':
        total_trades, wins = get_symbol_performance(sym)
        
        # EXTREME FEATURE 4: Kelly Criterion Auto-Compounding
        # 1. Calculate Real Dynamic Capital (Initial + Total Profit)
        dynamic_capital = 10000.0
        try:
            if os.path.exists('trades_log.csv'):
                with open('trades_log.csv', 'r') as f_log:
                    lines = f_log.readlines()[1:] # skip header
                    for line in lines:
                        parts = line.strip().split(',')
                        if len(parts) >= 6 and parts[1] == 'SELL':
                            dynamic_capital += float(parts[5]) # Add profit
        except: pass
        
        if total_trades >= 3:
            win_rate = wins / total_trades
            # Kelly % = (2 * WinRate) - 1
            kelly_pct = max(0.05, min(0.60, (2 * win_rate - 1)))
            investment = dynamic_capital * kelly_pct
            thought += f" 🧠 [Auto-Compounding]: క్యాపిటల్ ₹{dynamic_capital:.0f} కి పెరిగింది! కాబట్టి {kelly_pct*100:.0f}% రిస్క్ చేస్తున్నా (₹{investment:.0f})!"
        else:
            investment = dynamic_capital * 0.20 # 20% default
 
            
        actual_trade_size = investment / current_price
        
        msg = f"🚀 BUY ఆర్డర్ ({sym}) @ ₹{current_price:.2f} (Qty: {actual_trade_size:.5f})\\n{thought}"
        voice_msg = f"Alert. Extreme AI Buying {sym.replace('-USD', ' crypto')}."
        log_status(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", voice_alert=voice_msg, color_code='[92m')
        log_trade("BUY", sym, current_price, actual_trade_size, 0.0)
        send_telegram_message(f"✅ {msg}")
        return sym
        
    elif signal == 'sell' and current_pos == 'BUY':
        last_buy, last_qty = get_last_buy_details(sym)
        profit = 0.0
        if last_buy > 0:
            profit = (current_price - last_buy) * last_qty
        
        msg = f"📉 SELL ఆర్డర్ ({sym}) (Qty: {last_qty:.5f}) | లాభం: ₹{profit:.4f}\\n{thought}"
        voice_msg = f"Alert. Extreme AI Selling {sym.replace('-USD', ' crypto')}."
        log_status(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", voice_alert=voice_msg, color_code='[91m')
        log_trade("SELL", sym, current_price, last_qty, profit)
        send_telegram_message(f"✅ {msg}")
        return sym
        
    return None

while True:
    try:
        actions_taken = []
        # EXTREME FEATURE 1: Multi-Threading
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(process_symbol, symbols_to_trade))
            
        actions_taken = [r for r in results if r is not None]
        
        if not actions_taken:
            log_status(f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ (Extreme Mode) అన్నీ ఒకేసారి స్కాన్ చేశాను. సేఫ్ గా HOLD లో ఉన్నాయి.", color_code='[96m')
            
    except Exception as e:
        log_status(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ ఎర్రర్: {e}")
        
    time.sleep(10) # 10 seconds scan in Extreme mode
