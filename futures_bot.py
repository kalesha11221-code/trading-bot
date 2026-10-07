import os
import db_helper
import time
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
    coin = sym.replace('-USD', '')
    binance_pair = f'{coin}USDT'
    try:
        url = f'https://api.binance.com/api/v3/klines?symbol={binance_pair}&interval=1m&limit=100'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            rows = []
            for k in data:
                rows.append({
                    'timestamp': datetime.fromtimestamp(k[0] / 1000.0),
                    'open': float(k[1]), 'high': float(k[2]),
                    'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])
                })
            df = pd.DataFrame(rows)
            return df
    except:
        return pd.DataFrame()

def generate_futures_signal(df):
    if df.empty or len(df) < 50: return 'HOLD', 0.0
    
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
    
    if last['EMA_9'] > last['EMA_21'] and last['close'] > last['EMA_50']:
        if prev['RSI'] < 35 and last['RSI'] > prev['RSI']:
            return 'LONG', last['close']
        if last['close'] > df['high'].iloc[-20:-1].max() * 0.999: 
            return 'LONG', last['close']

    if last['EMA_9'] < last['EMA_21'] and last['close'] < last['EMA_50']:
        if prev['RSI'] > 65 and last['RSI'] < prev['RSI']:
            return 'SHORT', last['close']
        if last['close'] < df['low'].iloc[-20:-1].min() * 1.001: 
            return 'SHORT', last['close']
            
    return 'HOLD', last['close']

def run_futures_bot():
    init_files()
    print("🚀 Futures Paper Bot Started (Leverage: 5x)")
    
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
                    if roe_pct >= 15.0:
                        should_close = True
                        reason = "TAKE_PROFIT"
                    elif roe_pct <= -10.0:
                        should_close = True
                        reason = "STOP_LOSS"
                    elif side == 'LONG' and signal == 'SHORT':
                        should_close = True
                        reason = "REVERSAL_SHORT"
                    elif side == 'SHORT' and signal == 'LONG':
                        should_close = True
                        reason = "REVERSAL_LONG"
                        
                    if should_close:
                        log_trade(sym, "CLOSE", side, entry, current_price, pos['margin'], LEVERAGE, round(pnl_inr, 2))
                        del state[sym]
                        save_state(state)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 CLOSED {side} {sym} | PnL: ₹{pnl_inr:.2f} ({reason})")
                        time.sleep(2)
                        
                elif len(state) < MAX_POSITIONS and signal != 'HOLD':
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
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 OPENED {signal} {sym} @ ${current_price:.2f}")
                    time.sleep(2)
                    
            time.sleep(10) 
            
        except Exception as e:
            print(f"Futures Bot Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_futures_bot()
