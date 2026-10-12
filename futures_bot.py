import os
import db_helper
import time
import ml_brain
import json

import urllib.request
import threading
import pandas as pd
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
FUTURES_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "DOGE-USD", "XRP-USD"]
LEVERAGE = 5
MARGIN_PER_TRADE = 5000.0  # ₹5000 per trade margin
MAX_POSITIONS = 3
USD_TO_INR = 84.5

STATE_FILE = 'fo_state.json'
LOG_FILE = 'fo_trades_log.csv'

file_lock = threading.Lock()

def init_files():
    with file_lock:
        if not os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'w') as f:
                json.dump({}, f)
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as f:
                f.write("Timestamp,Symbol,Action,Side,EntryPrice,ExitPrice,Margin,Leverage,Profit_INR\n")

def get_state():
    return db_helper.get_state('fo_state')

def save_state(state):
    db_helper.save_state('fo_state', state)

def log_trade(sym, action, side, entry_p, exit_p, margin, lev, profit):
    with file_lock:
        with open(LOG_FILE, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp},{sym},{action},{side},{entry_p},{exit_p},{margin},{lev},{profit}\n")

def fetch_binance_data(sym):
    # 1. Try Binance Direct API
    try:
        coin = sym.replace('-USD', '')
        binance_pair = f'{coin}USDT'
        url = f'https://api.binance.com/api/v3/klines?symbol={binance_pair}&interval=5m&limit=100'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            rows = []
            for k in data:
                rows.append({
                    'timestamp': datetime.fromtimestamp(k[0] / 1000.0),
                    'open': float(k[1]), 'high': float(k[2]),
                    'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])
                })
            df = pd.DataFrame(rows)
            if not df.empty and len(df) >= 30:
                return df
    except Exception:
        pass

    # 2. Cloud Fallback: Yahoo v8 Direct Chart API (Bypasses all Geo-Blocks & Cloud Bans!)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=1d'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            res = json.loads(resp.read().decode())
            chart = res['chart']['result'][0]
            timestamps = chart.get('timestamp', [])
            quote = chart['indicators']['quote'][0]
            if timestamps and 'close' in quote:
                rows = []
                for i in range(len(timestamps)):
                    c = quote['close'][i]
                    if c is not None:
                        rows.append({
                            'timestamp': datetime.fromtimestamp(timestamps[i]),
                            'open': float(quote.get('open', [c])[i] or c),
                            'high': float(quote.get('high', [c])[i] or c),
                            'low': float(quote.get('low', [c])[i] or c),
                            'close': float(c),
                            'volume': float(quote.get('volume', [100.0])[i] or 100.0)
                        })
                df = pd.DataFrame(rows)
                if not df.empty and len(df) >= 30:
                    return df
    except Exception:
        pass

    return pd.DataFrame()

def generate_futures_signal(df):
    if df.empty or len(df) < 30: return 'HOLD', 0.0
    
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 🟢 BULLISH MOMENTUM ENTRY (LONG 5x)
    # EMA 9 crosses above EMA 21 or strong trend with rising RSI
    if last['EMA_9'] > last['EMA_21']:
        if (last['close'] > last['EMA_50'] or (prev['RSI'] <= 45 and last['RSI'] > prev['RSI'])):
            if last['RSI'] < 72: # Avoid chasing at extreme overbought
                return 'LONG', last['close']
                
    # 🔴 BEARISH MOMENTUM ENTRY (SHORT 5x)
    # EMA 9 crosses below EMA 21 or strong downtrend with falling RSI
    if last['EMA_9'] < last['EMA_21']:
        if (last['close'] < last['EMA_50'] or (prev['RSI'] >= 55 and last['RSI'] < prev['RSI'])):
            if last['RSI'] > 28: # Avoid chasing at extreme oversold
                return 'SHORT', last['close']
            
    return 'HOLD', last['close']

def run_futures_bot():
    init_files()
    cooldown_dict = {}
    print("🚀 Futures Paper Bot Started (Leverage: 5x)", flush=True)
    
    while True:
        try:
            state = get_state()
            open_symbols = list(state.keys())
            
            for sym in FUTURES_SYMBOLS:
                df = fetch_binance_data(sym)
                if df.empty: continue
                
                signal, current_price = generate_futures_signal(df)
                
                if sym in state:
                    pos = state[sym]
                    side = pos['side']
                    entry = pos['entry_price']
                    qty = pos['qty']
                    
                    if side == 'LONG':
                        pnl_usd = (current_price - entry) * qty
                    else: 
                        pnl_usd = (entry - current_price) * qty
                        
                    pnl_inr = pnl_usd * USD_TO_INR
                    roe_pct = (pnl_inr / pos['margin']) * 100
                    
                    should_close = False
                    if roe_pct >= 10.0:
                        should_close = True
                        reason = "TAKE_PROFIT"
                    elif roe_pct <= -10.0:
                        should_close = True
                        reason = "STOP_LOSS"
                    elif side == 'LONG' and signal == 'SHORT' and roe_pct >= 5.0:
                        should_close = True
                        reason = "REVERSAL_PROFIT_LOCK"
                    elif side == 'SHORT' and signal == 'LONG' and roe_pct >= 5.0:
                        should_close = True
                        reason = "REVERSAL_PROFIT_LOCK"
                        
                    if should_close:
                        log_trade(sym, "CLOSE", side, entry, current_price, pos['margin'], LEVERAGE, round(pnl_inr, 2))
                        del state[sym]
                        save_state(state)
                        cooldown_dict[sym] = time.time() + 300
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 CLOSED {side} {sym} | PnL: ₹{pnl_inr:.2f} ({reason})", flush=True)
                        time.sleep(2)
                        
                elif len(state) < MAX_POSITIONS and signal != 'HOLD':
                    if time.time() < cooldown_dict.get(sym, 0):
                        continue
                    qty_usd = (MARGIN_PER_TRADE / USD_TO_INR) * LEVERAGE
                    coin_qty = qty_usd / current_price
                    
                    state[sym] = {
                        "side": signal,
                        "entry_price": current_price,
                        "qty": coin_qty,
                        "margin": MARGIN_PER_TRADE,
                        "leverage": LEVERAGE,
                        "timestamp": datetime.now().isoformat()
                    }
                    save_state(state)
                    log_trade(sym, "OPEN", signal, current_price, 0, MARGIN_PER_TRADE, LEVERAGE, 0.0)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 OPENED {signal} {sym} @ ${current_price:.2f}", flush=True)
                    time.sleep(2)
                    
            time.sleep(10) 
            
        except Exception as e:
            print(f"Futures Bot Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_futures_bot()
