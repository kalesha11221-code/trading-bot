import os
import db_helper
import time
import ml_brain
import json

import urllib.request
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Returns current datetime in Indian Standard Time (IST)."""
    return datetime.now(IST)

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
        # Restore full trade history from MongoDB Cloud so restarts never lose history
        db_helper.sync_cloud_to_local(is_futures=True)
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as f:
                f.write("Timestamp,Symbol,Action,Side,EntryPrice,ExitPrice,Margin,Leverage,Profit_INR\n")

def get_state():
    return db_helper.get_state('fo_state')

def save_state(state):
    db_helper.save_state('fo_state', state)

def log_trade(sym, action, side, entry_p, exit_p, margin, lev, profit):
    with file_lock:
        timestamp = get_ist_now().strftime('%Y-%m-%d %H:%M:%S')
        trade_data = {
            'Timestamp': timestamp,
            'Symbol': sym,
            'Action': action,
            'Side': side,
            'EntryPrice': entry_p,
            'ExitPrice': exit_p,
            'Margin': margin,
            'Leverage': lev,
            'Profit_INR': profit
        }
        db_helper.log_trade_persistent(trade_data, is_futures=True)

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

def generate_futures_signal(df, sym="BTC-USD"):
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
    
    # 🏛️ Institutional Confluence: Consult ml_brain (SMC + Machine Learning)
    ml_sig = ml_brain.get_ml_signal(sym)
    smc_info = ml_brain.get_smc_analysis(sym)
    smc_bias = smc_info.get("bias", "NEUTRAL")
    
    # Candlestick Confirmation Guard
    is_candle_bullish = (last['close'] >= last['open']) or (last['close'] >= prev['close'])
    is_candle_bearish = (last['close'] <= last['open']) or (last['close'] <= prev['close'])
    
    # 🟢 INSTITUTIONAL BULLISH ENTRY (LONG 5x)
    # EMA 9 > 21 + RSI momentum + ML == 1 + (SMC Bullish or Neutral) + Bullish Candle
    if last['EMA_9'] > last['EMA_21'] and last['RSI'] < 72 and is_candle_bullish:
        if (last['close'] > last['EMA_50'] or (prev['RSI'] <= 45 and last['RSI'] > prev['RSI'])):
            if ml_sig == 1 and smc_bias != "BEARISH":
                return 'LONG', last['close']
                
    # 🔴 INSTITUTIONAL BEARISH ENTRY (SHORT 5x)
    # EMA 9 < 21 + RSI dropping + ML == 0 + (SMC Bearish or Neutral) + Bearish Candle
    if last['EMA_9'] < last['EMA_21'] and last['RSI'] > 28 and is_candle_bearish:
        if (last['close'] < last['EMA_50'] or (prev['RSI'] >= 55 and last['RSI'] < prev['RSI'])):
            if ml_sig == 0 and smc_bias != "BULLISH":
                return 'SHORT', last['close']
            
    return 'HOLD', last['close']

def run_futures_bot():
    init_files()
    cooldown_dict = {}
    print("🚀 Institutional Futures Paper Bot Started (Leverage: 5x | SMC & Trailing Engine)", flush=True)
    
    while True:
        try:
            state = get_state()
            open_symbols = list(state.keys())
            
            for sym in FUTURES_SYMBOLS:
                df = fetch_binance_data(sym)
                if df.empty: continue
                
                signal, current_price = generate_futures_signal(df, sym)
                
                if sym in state:
                    pos = state[sym]
                    side = pos['side']
                    entry = pos['entry_price']
                    qty = pos['qty']
                    margin = float(pos['margin'])
                    
                    if side == 'LONG':
                        pnl_usd = (current_price - entry) * qty
                    else: 
                        pnl_usd = (entry - current_price) * qty
                        
                    # 🏛️ INSTITUTIONAL FEE-AWARE P&L ENGINE
                    # Margin: ₹5,000 | Leverage: 5x | Notional: ₹25,000
                    # Roundtrip Taker Fee: 0.10% on ₹25,000 = ₹25.00 (0.50% ROE)
                    fee_inr = margin * LEVERAGE * 0.001  # Exact ₹25 roundtrip fee
                    net_pnl_inr = pnl_inr - fee_inr
                    net_roe_pct = (net_pnl_inr / margin) * 100.0

                    # Track Peak ROE for trailing profit
                    peak_roe = max(pos.get('peak_roe', 0.0), roe_pct)
                    pos['peak_roe'] = peak_roe
                    save_state(state)
                    
                    should_close = False
                    reason = ""
                    
                    # 1. 🎯 FAST SCALPING TAKE PROFIT (+3.5% ROE = +₹175 gross | +₹150 NET PROFIT after fee)
                    # Quickly captures 0.7% micro-momentum spikes in 3-10 minutes!
                    if roe_pct >= 3.5:
                        should_close = True
                        reason = f"TAKE_PROFIT_TARGET (+3.5% ROE | Net: +₹{net_pnl_inr:.2f})"
                    
                    # 2. 🛡️ DYNAMIC TRAILING PROFIT LOCK (Peak >= +3.0% ROE, locks profit if dips 0.8%)
                    elif peak_roe >= 3.0 and roe_pct <= (peak_roe - 0.8):
                        should_close = True
                        reason = f"TRAILING_PROFIT_LOCK (Peak: +{peak_roe:.1f}%, Net: +₹{net_pnl_inr:.2f})"
                        
                    # 3. 🔒 FEE-AWARE TRUE BREAKEVEN LOCK
                    # If trade went up to +2.0% ROE earlier, lock exit at +1.0% ROE (+₹50 gross | +₹25 NET)
                    elif peak_roe >= 2.0 and roe_pct <= 1.0:
                        should_close = True
                        reason = f"TRUE_BREAKEVEN_NET_LOCK (+1.0% ROE | Net: +₹{net_pnl_inr:.2f})"
                        
                    # 4. 🔄 CONFIRMED REVERSAL EXIT (Must have at least +1.5% ROE | Net +₹50)
                    elif (side == 'LONG' and signal == 'SHORT' and roe_pct >= 1.5) or (side == 'SHORT' and signal == 'LONG' and roe_pct >= 1.5):
                        should_close = True
                        reason = f"REVERSAL_NET_PROFIT_LOCK (Net: +₹{net_pnl_inr:.2f})"
                        
                    # 5. 🛑 STRICT RISK GUARD / STOP LOSS (-2.5% ROE = ₹125 max loss)
                    elif roe_pct <= -2.5:
                        should_close = True
                        reason = f"HARD_STOP_LOSS (-2.5% ROE | Capital Protected)"
                        
                    if should_close:
                        log_trade(sym, "CLOSE", side, entry, current_price, margin, LEVERAGE, round(pnl_inr, 2))
                        del state[sym]
                        save_state(state)
                        cooldown_dict[sym] = time.time() + 300
                        print(f"[{get_ist_now().strftime('%H:%M:%S IST')}] 🛑 CLOSED {side} {sym} | PnL: ₹{pnl_inr:.2f} ({reason})", flush=True)
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
                        "peak_roe": 0.0,
                        "timestamp": get_ist_now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    save_state(state)
                    log_trade(sym, "OPEN", signal, current_price, 0, MARGIN_PER_TRADE, LEVERAGE, 0.0)
                    print(f"[{get_ist_now().strftime('%H:%M:%S IST')}] 🏛️ OPENED {signal} {sym} @ ${current_price:.2f} [Institutional Confluence]", flush=True)
                    time.sleep(2)
                    
            time.sleep(10) 
            
        except Exception as e:
            print(f"Futures Bot Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_futures_bot()
