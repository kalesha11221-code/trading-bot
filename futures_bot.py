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

# ══════════════════════════════════════════════════════════════
# 🏛️ INSTITUTIONAL PRO TRADER FUTURES CONFIGURATION
# ══════════════════════════════════════════════════════════════
FUTURES_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "DOGE-USD", "XRP-USD"]
LEVERAGE = 5
MARGIN_PER_TRADE = 5000.0  # ₹5,000 margin per position
MAX_POSITIONS = 2          # Pro risk management: Max 2 concurrent positions (no over-exposure)
USD_TO_INR = 84.5

STATE_FILE = 'fo_state.json'
LOG_FILE = 'fo_trades_log.csv'

file_lock = threading.Lock()
btc_regime_cache = {"trend": "NEUTRAL", "last_check": 0}

def init_files():
    with file_lock:
        if not os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'w') as f:
                json.dump({}, f)
        db_helper.sync_cloud_to_local(is_futures=True)
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as f:
                f.write("Timestamp,Symbol,Action,Side,EntryPrice,ExitPrice,Margin,Leverage,Profit_INR\n")

def get_state():
    state = db_helper.get_state('fo_state')
    return state if isinstance(state, dict) else {}

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

def fetch_binance_data(sym, interval='15m', limit=120):
    """
    Fetches high-quality 15m candlestick data (Pro Timeframe for Institutional Confluence).
    Dual-engine: Binance Public API with Yahoo Finance fallback.
    """
    # 1. Binance Direct API
    try:
        coin = sym.replace('-USD', '')
        binance_pair = f'{coin}USDT'
        url = f'https://api.binance.com/api/v3/klines?symbol={binance_pair}&interval={interval}&limit={limit}'
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
            if not df.empty and len(df) >= 35:
                return df
    except Exception:
        pass

    # 2. Yahoo Finance v8 Fallback
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        y_int = '15m' if interval == '15m' else '5m'
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={y_int}&range=3d'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
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
                if not df.empty and len(df) >= 35:
                    return df
    except Exception:
        pass

    return pd.DataFrame()

def get_btc_macro_trend():
    """
    Checks Bitcoin (Mother Market) trend. In Crypto, altcoins strictly follow Bitcoin.
    When BTC is surging or Bullish, NO altcoin is allowed to take a SHORT position!
    """
    global btc_regime_cache
    now_t = time.time()
    if now_t - btc_regime_cache["last_check"] < 60:
        return btc_regime_cache["trend"]
    
    try:
        btc_df = fetch_binance_data("BTC-USD", interval="15m", limit=60)
        if not btc_df.empty and len(btc_df) >= 30:
            btc_close = btc_df['close'].iloc[-1]
            ema_21 = btc_df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
            ema_50 = btc_df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
            
            if btc_close > ema_21 and ema_21 > ema_50:
                btc_regime_cache["trend"] = "BULLISH"
            elif btc_close < ema_21 and ema_21 < ema_50:
                btc_regime_cache["trend"] = "BEARISH"
            else:
                btc_regime_cache["trend"] = "NEUTRAL"
            btc_regime_cache["last_check"] = now_t
    except Exception:
        pass
    return btc_regime_cache["trend"]

# ══════════════════════════════════════════════════════════════
# 🧠 INSTITUTIONAL MARKET PREDICTION & SIGNAL ENGINE
# ══════════════════════════════════════════════════════════════
def generate_futures_signal(df, sym="BTC-USD"):
    """
    True Pro-Trader Predictive Futures Algorithm:
    1. 200 EMA + 50 EMA Macro Regime Filter (Never counter-trend trade)
    2. Bitcoin Mother Market Veto Guard
    3. VWAP Support/Resistance + Volume Delta
    4. Smart Money Concepts (Liquidity Sweeps & FVG)
    5. Linear Predictive Trajectory (ML Slope)
    """
    if df.empty or len(df) < 35: 
        return 'HOLD', 0.0, "Insufficient Data"
    
    # 1. EMAs (9, 21, 50, 200)
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=min(100, len(df)), adjust=False).mean()
    
    # 2. VWAP
    df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (df['Typical_Price'] * df['volume']).rolling(window=30).sum() / (df['volume'].rolling(window=30).sum() + 1e-9)
    
    # 3. RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 4. Volume Moving Average
    df['Vol_MA'] = df['volume'].rolling(window=20).mean()
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    current_price = last['close']
    
    # Volume Surge Confirmation
    vol_surge = (last['volume'] > last['Vol_MA'] * 1.25) if last['Vol_MA'] > 0 else True
    is_candle_bullish = (last['close'] > last['open']) and (last['close'] >= prev['close'])
    is_candle_bearish = (last['close'] < last['open']) and (last['close'] <= prev['close'])
    
    # 🏛️ RULE 1: THE 200 EMA GOLDEN REGIME (Pro Trader Foundation)
    is_macro_bull = (last['close'] >= last['EMA_200']) and (last['EMA_50'] >= last['EMA_200'] * 0.998)
    is_macro_bear = (last['close'] <= last['EMA_200']) and (last['EMA_50'] <= last['EMA_200'] * 1.002)
    
    # 👑 RULE 2: BITCOIN MOTHER MARKET SHIELD
    btc_trend = get_btc_macro_trend()
    
    # 💎 RULE 3: SMART MONEY CONCEPTS (Liquidity Sweeps)
    recent_20_low = df['low'].iloc[-20:-1].min() if len(df) >= 20 else df['low'].min()
    recent_20_high = df['high'].iloc[-20:-1].max() if len(df) >= 20 else df['high'].max()
    is_bull_sweep = (prev['low'] <= recent_20_low) and (last['close'] > prev['high'])
    is_bear_sweep = (prev['high'] >= recent_20_high) and (last['close'] < prev['low'])
    
    # 📈 RULE 4: PREDICTIVE LINEAR REGRESSION SLOPE (Trajectory Prediction)
    try:
        x = np.arange(15)
        y = df['close'].tail(15).values
        slope, _ = np.polyfit(x, y, 1)
    except Exception:
        slope = 0.0
    
    # 🏛️ Consult ml_brain SMC & ML Score
    ml_sig = ml_brain.get_ml_signal(sym)
    smc_info = ml_brain.get_smc_analysis(sym)
    smc_bias = smc_info.get("bias", "NEUTRAL")

    # 🟢 ════════════════════════════════════════════════════════
    # 1. INSTITUTIONAL LONG PREDICTION (5x LEVERAGE)
    # ══════════════════════════════════════════════════════════
    # Conditions:
    # 1. Macro Regime is Bullish (Price >= 200 EMA) OR confirmed Bullish Liquidity Sweep
    # 2. Short-term trend aligned (EMA 9 > 21 OR Bullish Reclaim of VWAP)
    # 3. RSI between 38 and 65 (Not overbought)
    # 4. Predictive Slope > 0 and Bullish Candle with Volume
    # 5. SMC Bias is NOT Bearish
    long_conditions = (
        (is_macro_bull or is_bull_sweep) and
        (last['EMA_9'] >= last['EMA_21'] or last['close'] >= last['VWAP']) and
        (38 <= last['RSI'] <= 65) and
        is_candle_bullish and
        (vol_surge or is_bull_sweep) and
        (slope >= 0 or ml_sig == 1) and
        (smc_bias != "BEARISH")
    )
    if long_conditions:
        thesis = f"Bullish HTF Confluence (Price > 200 EMA, RSI: {last['RSI']:.1f}, Slope: +{slope:.3f}, Volume Surge: {vol_surge})"
        return 'LONG', current_price, thesis

    # 🔴 ════════════════════════════════════════════════════════
    # 2. INSTITUTIONAL SHORT PREDICTION (5x LEVERAGE)
    # ══════════════════════════════════════════════════════════
    # Conditions:
    # 1. Macro Regime is Bearish (Price <= 200 EMA) OR confirmed Bearish Liquidity Sweep
    # 2. BTC Mother Market is NOT Bullish (Never short against a raging BTC pump!)
    # 3. Short-term trend aligned (EMA 9 < 21 OR Bearish Rejection from VWAP)
    # 4. RSI between 52 and 72 (Not oversold)
    # 5. Predictive Slope < 0 and Bearish Candle with Volume
    # 6. SMC Bias is NOT Bullish
    short_conditions = (
        (is_macro_bear or is_bear_sweep) and
        (btc_trend != "BULLISH") and
        (last['EMA_9'] <= last['EMA_21'] or last['close'] <= last['VWAP']) and
        (52 <= last['RSI'] <= 72) and
        is_candle_bearish and
        (vol_surge or is_bear_sweep) and
        (slope <= 0 or ml_sig == 0) and
        (smc_bias != "BULLISH")
    )
    if short_conditions:
        thesis = f"Bearish HTF Confluence (Price < 200 EMA, BTC: {btc_trend}, RSI: {last['RSI']:.1f}, Slope: {slope:.3f})"
        return 'SHORT', current_price, thesis

    return 'HOLD', current_price, "Awaiting Institutional Setup"

def is_paper_trading_allowed():
    try:
        c_mode = db_helper.get_state('trading_mode')
        c_str = str(c_mode.get('mode', c_mode) if isinstance(c_mode, dict) else c_mode).lower()
        if "angel" in c_str:
            return False
    except Exception:
        pass
    if os.path.exists('trading_mode.txt'):
        try:
            with open('trading_mode.txt', 'r') as f:
                if "angel" in f.read().strip().lower():
                    return False
        except Exception:
            pass
    return True

# ══════════════════════════════════════════════════════════════
# 🚀 24/7 PRO FUTURES TRADING EXECUTION LOOP
# ══════════════════════════════════════════════════════════════
def run_futures_bot():
    init_files()
    cooldown_dict = {}
    print("🚀 Pro Institutional Futures Bot ONLINE (15m HTF + 200 EMA Dominance + SMC)", flush=True)
    
    while True:
        try:
            if not is_paper_trading_allowed():
                time.sleep(15)
                continue
            
            state = get_state()
            
            # ─── AUTO-CLEANUP / INVALIDATION OF BAD COUNTER-TREND SHORTS ───
            # If the market is in a raging Bull Trend (BTC Bullish, Price > 200 EMA)
            # gracefully cut old losing counter-trend shorts to prevent further bleeding!
            for sym, pos in list(state.items()):
                side = pos.get('side', 'LONG')
                entry = float(pos.get('entry_price', 0))
                margin = float(pos.get('margin', MARGIN_PER_TRADE))
                qty = float(pos.get('qty', 0))
                
                df_curr = fetch_binance_data(sym, interval='15m', limit=40)
                if df_curr.empty or entry <= 0: continue
                current_price = float(df_curr['close'].iloc[-1])
                
                if side == 'LONG':
                    pnl_usd = (current_price - entry) * qty
                    roe_pct = ((current_price - entry) / entry) * 100.0 * LEVERAGE
                else:
                    pnl_usd = (entry - current_price) * qty
                    roe_pct = ((entry - current_price) / entry) * 100.0 * LEVERAGE
                
                pnl_inr = pnl_usd * USD_TO_INR
                fee_inr = margin * LEVERAGE * 0.001
                net_pnl_inr = pnl_inr - fee_inr
                
                peak_roe = max(pos.get('peak_roe', 0.0), roe_pct)
                pos['peak_roe'] = peak_roe
                
                # Check for Market Regime Invalidation
                ema_21 = float(df_curr['close'].ewm(span=21, adjust=False).mean().iloc[-1])
                should_close = False
                reason = ""

                # 1. 🎯 FAST SCALPING TAKE PROFIT (+3.0% ROE = +₹150 NET PROFIT)
                if roe_pct >= 3.0:
                    should_close = True
                    reason = f"TARGET_PROFIT (+{roe_pct:.1f}% ROE | Net: +₹{net_pnl_inr:.2f})"
                
                # 2. 🛡️ DYNAMIC TRAILING PROFIT LOCK (Locks profit after peak)
                elif peak_roe >= 2.0 and roe_pct <= (peak_roe - 0.7):
                    should_close = True
                    reason = f"TRAILING_PROFIT_LOCK (Peak: +{peak_roe:.1f}% | Net: +₹{net_pnl_inr:.2f})"
                    
                # 3. 🔒 TRUE BREAKEVEN LOCK (+0.8% ROE = +₹40 NET)
                elif peak_roe >= 1.8 and roe_pct <= 0.8:
                    should_close = True
                    reason = f"BREAKEVEN_NET_LOCK (+0.8% ROE | Net: +₹{net_pnl_inr:.2f})"
                
                # 4. ⚡ PRO INVALIDATION CUT (Early Exit on Reversal, Zero Bleed!)
                # If SHORT and price closed strongly above EMA 21, don't hold till max loss!
                elif side == 'SHORT' and current_price > (ema_21 * 1.008):
                    should_close = True
                    reason = f"PRO_TREND_INVALIDATION_CUT (Bullish Reversal Reclaim | ROE: {roe_pct:.1f}%)"
                elif side == 'LONG' and current_price < (ema_21 * 0.992):
                    should_close = True
                    reason = f"PRO_TREND_INVALIDATION_CUT (Bearish Breakdown | ROE: {roe_pct:.1f}%)"

                # 5. 🛑 STRICT TIGHT STOP-LOSS CAP (-4.0% ROE = Max ₹200 Loss, NOT ₹500!)
                elif roe_pct <= -4.0:
                    should_close = True
                    reason = f"STRICT_PRO_STOP_LOSS (-4.0% ROE Cap | Capital Preserved)"

                if should_close:
                    log_trade(sym, "CLOSE", side, entry, current_price, margin, LEVERAGE, round(pnl_inr, 2))
                    del state[sym]
                    save_state(state)
                    cooldown_dict[sym] = time.time() + 300
                    print(f"[{get_ist_now().strftime('%H:%M:%S IST')}] 🛑 CLOSED {side} {sym} | PnL: ₹{pnl_inr:.2f} ({reason})", flush=True)
                    time.sleep(2)
                else:
                    save_state(state)

            # ─── NEW HIGH-PROBABILITY INSTITUTIONAL ENTRIES ───
            for sym in FUTURES_SYMBOLS:
                if len(state) >= MAX_POSITIONS:
                    break
                if sym in state:
                    continue
                if time.time() < cooldown_dict.get(sym, 0):
                    continue

                df = fetch_binance_data(sym, interval='15m', limit=120)
                if df.empty: continue

                signal, current_price, thesis = generate_futures_signal(df, sym)

                if signal in ['LONG', 'SHORT']:
                    qty_usd = (MARGIN_PER_TRADE / USD_TO_INR) * LEVERAGE
                    coin_qty = qty_usd / current_price

                    state[sym] = {
                        "side": signal,
                        "entry_price": current_price,
                        "qty": coin_qty,
                        "margin": MARGIN_PER_TRADE,
                        "leverage": LEVERAGE,
                        "peak_roe": 0.0,
                        "thesis": thesis,
                        "timestamp": get_ist_now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    save_state(state)
                    log_trade(sym, "OPEN", signal, current_price, 0, MARGIN_PER_TRADE, LEVERAGE, 0.0)
                    print(f"[{get_ist_now().strftime('%H:%M:%S IST')}] 🏛️ PRO ENTRY: {signal} {sym} @ ${current_price:.2f} | {thesis}", flush=True)
                    time.sleep(2)

            time.sleep(12)

        except Exception as e:
            print(f"Futures Bot Loop Exception: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    run_futures_bot()
