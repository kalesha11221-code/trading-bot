import os
import json
import time
import urllib.request
import warnings
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore")

# Global caches
signal_cache = {}
smc_cache = {}
CACHE_DURATION = 1800  # 30 minutes cache for optimal balance between accuracy & speed

def fetch_klines(symbol, interval='1h', limit=150):
    """
    Dual-engine data fetcher: Binance Public API with Yahoo v8 fallback.
    Supports both Crypto (24/7) and Indian NSE Stocks.
    """
    # 1. Binance Public API (for Crypto)
    if not ('.NS' in symbol or '.BO' in symbol):
        try:
            b_sym = symbol.replace('-USD', 'USDT')
            url = f"https://api.binance.com/api/v3/klines?symbol={b_sym}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list) and len(data) > 0:
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
                    if len(df) >= 30:
                        return df
        except Exception:
            pass

    # 2. Yahoo Finance v8 Fallback (Bypasses Geo-blocks & supports Indian Stocks)
    try:
        y_interval = '60m' if interval == '1h' else ('15m' if interval == '15m' else '5m')
        y_range = '15d' if interval == '1h' else '5d'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={y_interval}&range={y_range}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
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
                if len(df) >= 30:
                    return df
    except Exception:
        pass

    return pd.DataFrame()

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

# ══════════════════════════════════════════════════════════════
# 🏛️ SMART MONEY CONCEPTS (SMC) DETECTION ALGORITHMS
# ══════════════════════════════════════════════════════════════

def detect_smc_features(df):
    """
    Computes professional institutional metrics:
    1. Fair Value Gap (FVG)
    2. Order Blocks (OB)
    3. Liquidity Sweeps
    4. Market Structure Trend
    """
    if df.empty or len(df) < 20:
        return df

    df = df.copy()
    
    # Initialize SMC columns
    df['fvg_bull'] = 0
    df['fvg_bear'] = 0
    df['ob_bull'] = 0
    df['ob_bear'] = 0
    df['liquidity_sweep'] = 0

    # 1. Fair Value Gaps (3-Candle Imbalance)
    for i in range(2, len(df)):
        c1_high = df['high'].iloc[i-2]
        c1_low = df['low'].iloc[i-2]
        c3_high = df['high'].iloc[i]
        c3_low = df['low'].iloc[i]

        if c3_low > c1_high:
            df.iloc[i, df.columns.get_loc('fvg_bull')] = 1
        elif c3_high < c1_low:
            df.iloc[i, df.columns.get_loc('fvg_bear')] = 1

    # 2. Institutional Order Blocks
    vol_mean = df['volume'].rolling(window=10).mean()
    for i in range(3, len(df)):
        curr_vol = df['volume'].iloc[i]
        avg_vol = vol_mean.iloc[i] if not np.isnan(vol_mean.iloc[i]) else 1.0
        
        # Bullish displacement
        if df['close'].iloc[i] > df['high'].iloc[i-1] and curr_vol > (avg_vol * 1.2):
            if df['close'].iloc[i-1] < df['open'].iloc[i-1]:
                df.iloc[i, df.columns.get_loc('ob_bull')] = 1
                
        # Bearish displacement
        elif df['close'].iloc[i] < df['low'].iloc[i-1] and curr_vol > (avg_vol * 1.2):
            if df['close'].iloc[i-1] > df['open'].iloc[i-1]:
                df.iloc[i, df.columns.get_loc('ob_bear')] = 1

    # 3. Liquidity Sweeps (Stop Hunts)
    high_10 = df['high'].shift(1).rolling(10).max()
    low_10 = df['low'].shift(1).rolling(10).min()
    for i in range(10, len(df)):
        prev_h = high_10.iloc[i]
        prev_l = low_10.iloc[i]
        c_h = df['high'].iloc[i]
        c_l = df['low'].iloc[i]
        c_c = df['close'].iloc[i]
        
        # Bearish Sweep: Swept high then rejected down (Whales dumped)
        if c_h > prev_h and c_c < prev_h:
            df.iloc[i, df.columns.get_loc('liquidity_sweep')] = -1
        # Bullish Sweep: Swept low then rejected up (Whales accumulated)
        elif c_l < prev_l and c_c > prev_l:
            df.iloc[i, df.columns.get_loc('liquidity_sweep')] = 1

    return df

def get_smc_analysis(symbol):
    """
    Provides a real-time institutional snapshot for a symbol:
    - Bias: BULLISH / BEARISH / NEUTRAL
    - Key SMC Triggers: FVG, Order Block, Liquidity Sweep
    - Multi-timeframe trend alignment
    """
    global smc_cache
    now = time.time()
    if symbol in smc_cache:
        cached_t, cached_res = smc_cache[symbol]
        if now - cached_t < 180:  # 3 min cache
            return cached_res

    df_1h = fetch_klines(symbol, interval='1h', limit=60)
    if df_1h.empty or len(df_1h) < 25:
        return {
            "bias": "NEUTRAL",
            "score": 0.0,
            "htf_trend": "SIDEWAYS",
            "fvg": False,
            "order_block": False,
            "liquidity_sweep": False
        }

    df_smc = detect_smc_features(df_1h)

    # HTF Trend (20 EMA vs 50 EMA)
    ema_20 = df_smc['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema_50 = df_smc['close'].ewm(span=50, adjust=False).mean().iloc[-1]
    htf_trend = "BULLISH" if ema_20 > ema_50 else "BEARISH"

    # Recent SMC signals (last 3 candles)
    recent = df_smc.iloc[-3:]
    has_bull_fvg = (recent['fvg_bull'] == 1).any()
    has_bear_fvg = (recent['fvg_bear'] == 1).any()
    has_bull_ob = (recent['ob_bull'] == 1).any()
    has_bear_ob = (recent['ob_bear'] == 1).any()
    has_bull_sweep = (recent['liquidity_sweep'] == 1).any()
    has_bear_sweep = (recent['liquidity_sweep'] == -1).any()

    bull_score = (2 if htf_trend == "BULLISH" else 0) + (1.5 if has_bull_fvg else 0) + (2 if has_bull_ob else 0) + (2.5 if has_bull_sweep else 0)
    bear_score = (2 if htf_trend == "BEARISH" else 0) + (1.5 if has_bear_fvg else 0) + (2 if has_bear_ob else 0) + (2.5 if has_bear_sweep else 0)

    if bull_score > bear_score and bull_score >= 3.5:
        bias = "BULLISH"
        score = bull_score
    elif bear_score > bull_score and bear_score >= 3.5:
        bias = "BEARISH"
        score = bear_score
    else:
        bias = "NEUTRAL"
        score = max(bull_score, bear_score)

    result = {
        "bias": bias,
        "score": round(score, 1),
        "htf_trend": htf_trend,
        "fvg": has_bull_fvg if bias == "BULLISH" else (has_bear_fvg if bias == "BEARISH" else False),
        "order_block": has_bull_ob if bias == "BULLISH" else (has_bear_ob if bias == "BEARISH" else False),
        "liquidity_sweep": has_bull_sweep if bias == "BULLISH" else (has_bear_sweep if bias == "BEARISH" else False)
    }

    smc_cache[symbol] = (now, result)
    return result

# ══════════════════════════════════════════════════════════════
# 🧠 ENHANCED RANDOM FOREST CLASSIFIER (INSTITUTIONAL BRAIN)
# ══════════════════════════════════════════════════════════════

def get_ml_signal(symbol):
    """
    Institutional Machine Learning Engine:
    Combines Technicals + Smart Money Concepts + Higher Timeframe Trends.
    Returns:
       1 = Strong Bullish / Institutional PUMP expected
       0 = Strong Bearish / Institutional DUMP expected
    """
    global signal_cache
    now = time.time()

    if symbol in signal_cache:
        cached_time, cached_signal = signal_cache[symbol]
        if now - cached_time < CACHE_DURATION:
            return cached_signal

    try:
        df = fetch_klines(symbol, interval='1h', limit=200)
        if df.empty or len(df) < 50:
            return 1  # Safe fallback

        # 1. Enrich with SMC features
        df = detect_smc_features(df)

        # 2. Add Quantitative Technical Features
        df['SMA_10'] = df['close'].rolling(window=10).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['RSI_14'] = calculate_rsi(df['close'], 14)
        df['Volatility'] = df['close'].rolling(window=10).std()
        df['Returns'] = df['close'].pct_change()

        # Institutional Net Bias Feature
        df['SMC_Net'] = (df['fvg_bull'] * 1.0 - df['fvg_bear'] * 1.0) + \
                        (df['ob_bull'] * 1.5 - df['ob_bear'] * 1.5) + \
                        (df['liquidity_sweep'] * 2.0)

        # Target: Will price go UP in the next 3 candles? (1 = Yes, 0 = No)
        df['Target'] = (df['close'].shift(-3) > df['close']).astype(int)
        df.dropna(inplace=True)

        features = ['SMA_10', 'SMA_50', 'EMA_20', 'RSI_14', 'Volatility', 'Returns', 'SMC_Net']

        X = df[features][:-1]
        y = df['Target'][:-1]

        if len(X) < 30:
            return 1

        # Train lightweight model (Memory-safe for Render 512MB RAM)
        model = RandomForestClassifier(n_estimators=40, max_depth=5, random_state=42, n_jobs=1)
        model.fit(X, y)

        # Predict latest candle
        latest_data = df[features].iloc[-1:]
        prediction = int(model.predict(latest_data)[0])

        signal_cache[symbol] = (now, prediction)
        bias_str = "🟢 INSTITUTIONAL PUMP (BULLISH)" if prediction == 1 else "🔴 INSTITUTIONAL DUMP (BEARISH)"
        print(f"🏛️ [AI SMC+ML] {symbol} Prediction: {bias_str}", flush=True)

        return prediction

    except Exception as e:
        print(f"⚠️ ML Error for {symbol}: {e}", flush=True)
        return 1
