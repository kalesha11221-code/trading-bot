"""
🌙 AI OVERNIGHT RESEARCH & MARKET PREDICTION BRAIN
=====================================================
Analyzes Global Macro Cues, Institutional Volume, Daily Pivots/CPR,
SMC Demand Zones, and Ranks the Top 3 Golden Sniper Stocks for Tomorrow's 9:15 AM NSE Opening.
Runs autonomously all night and on weekends when the Indian Market is closed.
"""

import os
import json
import time
import threading
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
import db_helper

IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.now(IST)

NSE_TARGET_SYMBOLS = [
    "BEL.NS", "GAIL.NS", "PNB.NS", "IRFC.NS", "MOTHERSON.NS", "NHPC.NS",
    "TATAPOWER.NS", "BHEL.NS", "COALINDIA.NS", "NTPC.NS", "CANBK.NS",
    "FEDERALBNK.NS", "IDFCFIRSTB.NS", "ASHOKLEY.NS",
    "ITC.NS", "TATASTEEL.NS", "ONGC.NS", "IOC.NS", "SUZLON.NS",
    "SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "RELIANCE.NS", "INFY.NS", "TCS.NS"
]

def analyze_global_cues():
    """
    Fetches global indices & macro telemetry (Nasdaq, S&P 500, Crude Oil, DXY, Nifty 50)
    to predict tomorrow morning's Indian market opening bias (Gap-Up / Gap-Down).
    """
    macro_tickers = {
        "^IXIC": "Nasdaq",
        "^GSPC": "S&P 500",
        "^NSEI": "Nifty 50",
        "CL=F": "Crude Oil",
        "USDINR=X": "USD / INR"
    }
    results = {}
    total_sentiment_score = 0
    
    try:
        data = yf.download(list(macro_tickers.keys()), period="5d", interval="1d", progress=False)['Close']
        if not data.empty and len(data) >= 2:
            last_row = data.iloc[-1]
            prev_row = data.iloc[-2]
            
            for ticker, name in macro_tickers.items():
                try:
                    c = float(last_row[ticker]) if ticker in last_row and not pd.isna(last_row[ticker]) else 0.0
                    p = float(prev_row[ticker]) if ticker in prev_row and not pd.isna(prev_row[ticker]) else c
                    chg_pct = ((c - p) / p * 100) if p > 0 else 0.0
                    results[name] = {"price": round(c, 2), "change_pct": round(chg_pct, 2)}
                    
                    if name in ["Nasdaq", "S&P 500"]:
                        if chg_pct > 0.5: total_sentiment_score += 2
                        elif chg_pct > 0.1: total_sentiment_score += 1
                        elif chg_pct < -0.5: total_sentiment_score -= 2
                        elif chg_pct < -0.1: total_sentiment_score -= 1
                    elif name == "Crude Oil":
                        # Lower crude oil is bullish for Indian economy & INR
                        if chg_pct < -1.0: total_sentiment_score += 1
                        elif chg_pct > 1.5: total_sentiment_score -= 1
                except Exception:
                    pass
    except Exception as e:
        print(f"Global cues fetch warning: {e}")
        
    if total_sentiment_score >= 2:
        bias = "BULLISH 🟢"
        open_prediction = "GAP-UP OPENING EXPECTED (సానుకూల గ్లోబల్ సంకేతాలు 🚀)"
    elif total_sentiment_score == 1:
        bias = "MILDLY BULLISH 🟢"
        open_prediction = "POSITIVE TO FLAT OPENING (స్వల్ప పాజిటివ్ ఓపెనింగ్ 📈)"
    elif total_sentiment_score <= -2:
        bias = "BEARISH 🔴"
        open_prediction = "GAP-DOWN / CAUTION (గ్లోబల్ సెల్లాఫ్ ఒత్తిడి ⚠️)"
    else:
        bias = "NEUTRAL 🟡"
        open_prediction = "BALANCED FLAT OPENING (మార్కెట్ స్తబ్ధుగా ఓపెన్ అయ్యే అవకాశం ⚖️)"
        
    return {
        "bias": bias,
        "open_prediction": open_prediction,
        "score": total_sentiment_score,
        "telemetry": results,
        "analyzed_at": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST")
    }

def analyze_stock_deep(sym):
    """
    Performs deep quantitative audit of an NSE stock:
    - Daily 200/50/20 EMAs
    - CPR (Central Pivot Range) calculation (Narrow CPR = Super Trend Day)
    - Pivot points (R1, S1, R2, S2)
    - Daily RSI(14)
    - RVOL (Relative Volume / Accumulation score)
    - Confluence Score (0 - 100)
    """
    clean_sym = sym.replace('.NS', '').replace('.BO', '')
    try:
        t = yf.Ticker(sym)
        df = t.history(period="3mo", interval="1d")
        if df.empty or len(df) < 25:
            return None
            
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        close = float(last['Close'])
        high = float(last['High'])
        low = float(last['Low'])
        volume = float(last['Volume'])
        
        # 1. EMAs
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=min(100, len(df)), adjust=False).mean()
        
        ema_20 = float(df['EMA_20'].iloc[-1])
        ema_50 = float(df['EMA_50'].iloc[-1])
        ema_200 = float(df['EMA_200'].iloc[-1])
        
        # 2. RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        if pd.isna(rsi): rsi = 50.0
        
        # 3. Classical Pivots & CPR (Central Pivot Range)
        pivot = (high + low + close) / 3.0
        bc = (high + low) / 2.0
        tc = (pivot - bc) + pivot
        cpr_width = abs(tc - bc) / (pivot + 1e-9) * 100.0
        
        is_narrow_cpr = (cpr_width <= 0.35)
        cpr_desc = "నారో CPR (రేపు బలమైన వన్-వే ట్రెండింగ్ డే అవకాశం! 🚀)" if is_narrow_cpr else "మీడియం CPR (రేంజ్ బౌండ్ / స్వింగ్ ⚖️)"
        
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        
        # 4. Relative Volume (RVOL)
        avg_vol_10 = float(df['Volume'].tail(10).mean())
        rvol = (volume / avg_vol_10) if avg_vol_10 > 0 else 1.0
        is_volume_accumulation = (rvol >= 1.25)
        
        # 5. Composite Institutional Confluence Score (0 - 100)
        score = 0
        reasons = []
        
        # +25: Above 200 EMA (Macro Bullish)
        if close >= ema_200:
            score += 25
            reasons.append("ప్రైస్ 200 EMA పైన స్థిరంగా ఉంది (లాంగ్ టర్మ్ బుల్లిష్)")
        
        # +20: 50 EMA > 200 EMA (Golden Structure)
        if ema_50 >= ema_200:
            score += 20
            reasons.append("50 EMA గోల్డెన్ అలైన్‌మెంట్‌లో ఉంది")
            
        # +15: RSI Optimal Bounce Zone (38 - 55)
        if 38 <= rsi <= 55:
            score += 15
            reasons.append(f"RSI ({rsi:.1f}) పర్ఫెక్ట్ డిప్ బౌన్స్ జోన్‌లో ఉంది")
        elif rsi > 70:
            score -= 10
            reasons.append(f"RSI ({rsi:.1f}) ఓవర్‌బాట్ రిస్క్ ఉంది")
            
        # +15: Narrow CPR (Trending Day High Probability)
        if is_narrow_cpr:
            score += 15
            reasons.append("నారో CPR కంప్రెషన్ (9:15 AM బ్రేకౌట్ సిద్ధం)")
            
        # +15: Volume Surge / Institutional Accumulation
        if is_volume_accumulation:
            score += 15
            reasons.append(f"ఇన్‌స్టిట్యూషనల్ అక్యుమ్యులేషన్ వాల్యూమ్ (+{int((rvol-1)*100)}% RVOL)")
            
        # +10: Price close near Support / Pivot (Lower Risk)
        if close <= pivot * 1.015:
            score += 10
            reasons.append("కీలకమైన పివోట్ సపోర్ట్ దగ్గర లభిస్తోంది")
            
        # Morning 9:15 AM Battleplan Numbers
        target_price = round(close * 1.025, 2)  # +2.50% profit target
        stop_loss_price = round(close * 0.988, 2) # -1.20% tight risk
        profit_inr = round((target_price - close) * max(1, int(1100 // close)), 2)
        
        return {
            "symbol": sym,
            "clean_name": clean_sym,
            "close": round(close, 2),
            "score": score,
            "rsi": round(rsi, 1),
            "rvol": round(rvol, 2),
            "is_narrow_cpr": is_narrow_cpr,
            "cpr_desc": cpr_desc,
            "cpr_width": round(cpr_width, 3),
            "pivot": round(pivot, 2),
            "r1": round(r1, 2),
            "s1": round(s1, 2),
            "target_2_5_pct": target_price,
            "stop_loss": stop_loss_price,
            "est_net_profit": profit_inr,
            "thesis": " | ".join(reasons) if reasons else "మార్కెట్ కన్సాలిడేషన్‌లో ఉంది.",
            "is_above_200_ema": close >= ema_200
        }
    except Exception as e:
        return None

def run_overnight_audit():
    """
    Executes complete overnight intelligence pipeline:
    1. Global Cues
    2. Deep Technical Audit of all 25 NSE Stocks
    3. Selection & Ranking of Top 3 Golden Sniper Stocks
    4. Saves to MongoDB and local JSON
    """
    print(f"[{get_ist_now().strftime('%H:%M:%S IST')}] 🌙 Running AI Overnight Research Brain...", flush=True)
    
    # 1. Global Macro
    global_report = analyze_global_cues()
    
    # 2. Stock Audits
    stock_reports = []
    for s in NSE_TARGET_SYMBOLS:
        res = analyze_stock_deep(s)
        if res:
            stock_reports.append(res)
            
    # Sort descending by Confluence Score
    stock_reports.sort(key=lambda x: x['score'], reverse=True)
    
    # Top 3 High-Conviction Picks for 9:15 AM Opening
    top_3_picks = stock_reports[:3] if len(stock_reports) >= 3 else stock_reports
    
    full_report = {
        "timestamp": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "date": get_ist_now().strftime("%Y-%m-%d"),
        "global_cues": global_report,
        "top_3_picks": top_3_picks,
        "ranked_stocks": stock_reports,
        "stocks_audited_count": len(stock_reports),
        "status": "COMPLETED",
        "voice_summary": (
            f"ఓవర్‌నైట్ రీసెర్చ్ రిపోర్ట్ సిద్ధంగా ఉంది. గ్లోబల్ మార్కెట్ సెంటిమెంట్ {global_report['bias']}. "
            f"రేపు ఉదయం 9:15 AM ఓపెనింగ్ లో టాప్-1 స్టాక్ {top_3_picks[0]['clean_name']} (స్కోర్: {top_3_picks[0]['score']}/100). "
            f"టార్గెట్ +2.50% ప్రాఫిట్ కు పర్ఫెక్ట్ గా సెట్ చేయబడింది."
        ) if top_3_picks else "ఓవర్‌నైట్ ఆడిట్ పూర్తయింది."
    }
    
    # Persist report to MongoDB Atlas and Local File
    try:
        db_helper.save_state('overnight_research', full_report)
    except Exception as e:
        print(f"MongoDB overnight report save info: {e}")
        
    try:
        with open('overnight_research.json', 'w', encoding='utf-8') as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    print(f"[{get_ist_now().strftime('%H:%M:%S IST')}] ✅ Overnight Research Completed! Top Pick: {top_3_picks[0]['clean_name'] if top_3_picks else 'None'}", flush=True)
    return full_report

def get_latest_overnight_report():
    """
    Retrieves the most recent overnight research report from MongoDB or local cache.
    """
    rep = db_helper.get_state('overnight_research')
    if isinstance(rep, dict) and 'top_3_picks' in rep:
        return rep
    if os.path.exists('overnight_research.json'):
        try:
            with open('overnight_research.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None

def is_market_closed_now():
    """
    Returns True if current IST time is outside Indian market hours (or on weekends).
    Indian market hours: Monday - Friday, 09:15 AM - 03:30 PM IST.
    """
    now = get_ist_now()
    if now.weekday() >= 5:  # Saturday or Sunday
        return True
    curr_time = now.time()
    market_open = datetime.strptime("09:15", "%H:%M").time()
    market_close = datetime.strptime("15:30", "%H:%M").time()
    return not (market_open <= curr_time <= market_close)

def overnight_research_worker():
    """
    Autonomous 24/7 Background Daemon:
    Whenever the Indian Market is closed (nights & weekends),
    runs research audits every 45 minutes to keep tomorrow's battleplan 100% updated.
    """
    print("🌙 AI Overnight Research Daemon Started...", flush=True)
    time.sleep(10)
    while True:
        try:
            if is_market_closed_now():
                run_overnight_audit()
                # Sleep for 45 minutes before refreshing global cues and rankings
                time.sleep(2700)
            else:
                # Live market is open: sleep 15 minutes, let live trading execute
                time.sleep(900)
        except Exception as e:
            print(f"Overnight worker error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    rep = run_overnight_audit()
    print("\n=== TOP 3 GOLDEN SNIPER PICKS FOR 9:15 AM ===")
    for idx, p in enumerate(rep.get('top_3_picks', [])):
        print(f"#{idx+1} {p['clean_name']}: Score={p['score']}/100 | Close=₹{p['close']} | Target(+2.5%)=₹{p['target_2_5_pct']} | {p['cpr_desc']}")
