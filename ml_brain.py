import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import time
import warnings
warnings.filterwarnings("ignore")

# Cache to avoid retraining every minute (Train every 2 hours)
signal_cache = {}
CACHE_DURATION = 2 * 3600

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_ml_signal(symbol):
    """
    Trains a Random Forest on the fly using recent 1h data.
    Returns 1 (Bullish/PUMP expected) or 0 (Bearish/DUMP expected).
    """
    global signal_cache
    now = time.time()
    
    if symbol in signal_cache:
        cached_time, cached_signal = signal_cache[symbol]
        if now - cached_time < CACHE_DURATION:
            return cached_signal
            
    try:
        print(f"🧠 [AI] Fetching data & Training ML Model for {symbol}...")
        
        # Download 60 days of 1-hour data
        df = yf.download(symbol, period="60d", interval="1h", progress=False)
        
        if df.empty or len(df) < 50:
            return 1 # Fallback
            
        # Clean up multi-index columns if yfinance returns them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.copy()
            
        # Create Technical Features
        df['SMA_10'] = df['Close'].rolling(window=10).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['RSI_14'] = calculate_rsi(df['Close'], 14)
        df['Volatility'] = df['Close'].rolling(window=10).std()
        df['Returns'] = df['Close'].pct_change()
        
        # Target: Will the price go up in the next 4 hours? (1 = Yes, 0 = No)
        df['Target'] = (df['Close'].shift(-4) > df['Close']).astype(int)
        
        # Drop NaN
        df.dropna(inplace=True)
        
        # Features for training
        features = ['SMA_10', 'SMA_50', 'RSI_14', 'Volatility', 'Returns']
        
        X = df[features][:-1] # Exclude last row (we don't know the future of the last row)
        y = df['Target'][:-1]
        
        # Train Model (Lightweight for Render 512MB RAM)
        model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42, n_jobs=1)
        model.fit(X, y)
        
        # Predict the latest situation
        latest_data = df[features].iloc[-1:]
        prediction = model.predict(latest_data)[0]
        
        signal_cache[symbol] = (now, int(prediction))
        print(f"🤖 [AI] {symbol} Prediction updated: {'PUMP 🟢' if prediction == 1 else 'DUMP 🔴'}")
        
        return int(prediction)
        
    except Exception as e:
        print(f"⚠️ ML Error for {symbol}: {e}")
        return 1 # Fallback to allowing trades if ML fails
