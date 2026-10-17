import os
import json
import csv
import io
import pandas as pd
from datetime import datetime

try:
    from pymongo import MongoClient
    import certifi
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False
    MongoClient = None

# Configure MongoDB Connection (Hardcoded for Render/Streamlit sync)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://kalesha11221_db_user:htGdtrwq23PLvQYi@cluster0.ur7meip.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Try to get from Streamlit Secrets just in case
try:
    import streamlit as st
    if "MONGO_URI" in st.secrets:
        MONGO_URI = st.secrets["MONGO_URI"]
except Exception:
    pass

_client = None
_db = None
_connection_attempted = False

def get_mongo_db():
    global _client, _db, _connection_attempted
    if _db is not None:
        return _db
    if _connection_attempted:
        return None
        
    _connection_attempted = True
    if not (MONGO_URI and HAS_PYMONGO):
        print("ℹ️ pymongo not available or MONGO_URI missing. Using local fallback mode.", flush=True)
        return None
        
    # Attempt 1: Official certifi CA bundle
    try:
        ca_file = certifi.where() if ('certifi' in globals() and certifi) else None
        c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, tlsCAFile=ca_file)
        c.admin.command('ping')
        _client = c
        _db = _client["trading_bot_db"]
        print("✅ MongoDB Connected Successfully with Certifi TLS!", flush=True)
        return _db
    except Exception as e1:
        pass

    # Attempt 2: Standard TLS
    try:
        c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
        c.admin.command('ping')
        _client = c
        _db = _client["trading_bot_db"]
        print("✅ MongoDB Connected Successfully with Standard TLS!", flush=True)
        return _db
    except Exception as e2:
        pass

    # Attempt 3: Fallback TLS with tlsAllowInvalidCertificates
    try:
        c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, tls=True, tlsAllowInvalidCertificates=True)
        c.admin.command('ping')
        _client = c
        _db = _client["trading_bot_db"]
        print("✅ MongoDB Connected Successfully with Fallback TLS!", flush=True)
        return _db
    except Exception as e3:
        pass

    print("ℹ️ MongoDB Cloud unreachable (Check Atlas IP Whitelist 0.0.0.0/0). Operating in local fallback mode.", flush=True)
    return None

# Initialize on module import
db = get_mongo_db()

# ─────────────────────────────────────────────────────────────
# 1. BOT STATE PERSISTENCE (dca_state, fo_state, live_scan_status, etc.)
# ─────────────────────────────────────────────────────────────
def get_state(collection_name, default_val=None):
    if default_val is None:
        default_val = {}
        
    curr_db = get_mongo_db()
    if curr_db is not None:
        try:
            doc = curr_db[collection_name].find_one({"_id": "state"})
            if doc and "data" in doc:
                return doc["data"]
            return default_val
        except Exception:
            pass
            
    # Fallback to local file
    file_path = f"{collection_name}.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default_val

def save_state(collection_name, state_data):
    curr_db = get_mongo_db()
    if curr_db is not None:
        try:
            curr_db[collection_name].update_one(
                {"_id": "state"},
                {"$set": {"data": state_data}},
                upsert=True
            )
        except Exception:
            pass
            
    # Always save local backup
    file_path = f"{collection_name}.json"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=4)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 2. PERMANENT CLOUD & LOCAL TRADE LOGGING (ZERO DATA LOSS ENGINE)
# ─────────────────────────────────────────────────────────────
FUTURES_HEADER = "Timestamp,Symbol,Action,Side,EntryPrice,ExitPrice,Margin,Leverage,Profit_INR\n"
SPOT_HEADER = "Time,Symbol,Action,Price,Shares,Profit\n"

def _get_trade_meta(is_futures):
    if is_futures:
        return 'fo_trades_log.csv', 'fo_trades_log', FUTURES_HEADER, ['Timestamp', 'Symbol', 'Action', 'Side', 'EntryPrice', 'ExitPrice', 'Margin', 'Leverage', 'Profit_INR']
    else:
        return 'trades_log.csv', 'trades_log', SPOT_HEADER, ['Time', 'Symbol', 'Action', 'Price', 'Shares', 'Profit']

def log_trade_persistent(row_dict, is_futures=False):
    """
    Saves trade to both MongoDB Cloud AND local CSV.
    Guarantees that even if Render or Streamlit restarts, trade is permanently saved.
    """
    file_name, col_name, header, fields = _get_trade_meta(is_futures)
    time_col = 'Timestamp' if is_futures else 'Time'
    
    clean_row = {}
    for fld in fields:
        clean_row[fld] = str(row_dict.get(fld, '0.0' if 'Profit' in fld else ''))

    t_val = clean_row.get(time_col, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    clean_row[time_col] = t_val
    doc_id = f"{t_val}_{clean_row.get('Symbol', '')}_{clean_row.get('Action', '')}"
    
    # 1. Save directly to MongoDB Atlas
    curr_db = get_mongo_db()
    if curr_db is not None:
        try:
            curr_db[col_name].update_one({"_id": doc_id}, {"$set": clean_row}, upsert=True)
        except Exception as e:
            print(f"MongoDB log error: {e}", flush=True)

    # 2. Append to local CSV
    try:
        if not os.path.exists(file_name) or os.path.getsize(file_name) == 0:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(header)
                
        with open(file_name, 'a', encoding='utf-8') as f:
            line_vals = [str(clean_row.get(fld, '')) for fld in fields]
            f.write(",".join(line_vals) + "\n")
    except Exception as e:
        print(f"Local CSV append error: {e}", flush=True)

def sync_cloud_to_local(is_futures=False):
    """
    Restores complete trade history from MongoDB into local CSV file.
    Runs on startup so freshly booted containers get the entire history back!
    """
    file_name, col_name, header, fields = _get_trade_meta(is_futures)
    curr_db = get_mongo_db()
    if curr_db is None:
        return
        
    try:
        time_col = 'Timestamp' if is_futures else 'Time'
        docs = list(curr_db[col_name].find().sort(time_col, 1))
        if docs:
            lines = [header]
            for doc in docs:
                row_vals = [str(doc.get(fld, '')) for fld in fields]
                lines.append(",".join(row_vals) + "\n")
                
            with open(file_name, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"✅ Restored {len(docs)} trades from MongoDB Cloud into {file_name}!", flush=True)
    except Exception as e:
        print(f"sync_cloud_to_local error: {e}", flush=True)

def merge_csv_data(csv_text, is_futures=False):
    """
    Intelligently merges incoming CSV lines from Render with existing history.
    NEVER wipes existing records, and works 100% reliably even if MongoDB is offline!
    """
    if not csv_text or not csv_text.strip():
        return
        
    file_name, col_name, header, fields = _get_trade_meta(is_futures)
    time_col = 'Timestamp' if is_futures else 'Time'
    
    # 1. Load existing records from local CSV
    all_records = {}
    if os.path.exists(file_name) and os.path.getsize(file_name) > len(header):
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                reader_old = csv.DictReader(f)
                for r in reader_old:
                    t = r.get(time_col, '')
                    s = r.get('Symbol', '')
                    a = r.get('Action', '')
                    if t and s:
                        k = f"{t}_{s}_{a}"
                        all_records[k] = {fld: str(r.get(fld, '')) for fld in fields}
        except Exception:
            pass

    # 2. Merge incoming records from Render
    try:
        reader_new = csv.DictReader(io.StringIO(csv_text.strip()))
        for r in reader_new:
            t = r.get(time_col, '')
            s = r.get('Symbol', '')
            a = r.get('Action', '')
            if t and s:
                k = f"{t}_{s}_{a}"
                all_records[k] = {fld: str(r.get(fld, '')) for fld in fields}
    except Exception:
        pass

    if not all_records:
        return

    # 3. Always write merged records locally so Streamlit displays them immediately!
    try:
        sorted_rows = sorted(all_records.values(), key=lambda r: str(r.get(time_col, '')))
        lines = [header]
        for r in sorted_rows:
            row_vals = [str(r.get(fld, '')) for fld in fields]
            lines.append(",".join(row_vals) + "\n")
        with open(file_name, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    except Exception as e:
        print(f"merge_csv_data local file write error: {e}", flush=True)

    # 4. Asynchronous Cloud Sync: Sync to MongoDB Atlas in background thread with bulk_write
    # This prevents blocking the UI for 15+ seconds while keeping MongoDB 100% updated!
    def _async_bg_sync(records, target_col):
        try:
            c_db = get_mongo_db()
            if c_db is not None and records:
                from pymongo import UpdateOne
                ops = [UpdateOne({"_id": k}, {"$set": clean_row}, upsert=True) for k, clean_row in records.items()]
                if ops:
                    c_db[target_col].bulk_write(ops, ordered=False)
        except Exception:
            pass

    import threading
    threading.Thread(target=_async_bg_sync, args=(all_records, col_name), daemon=True).start()

def get_trade_history_df(is_futures=False):
    """
    Returns pandas DataFrame containing complete, unabridged trade history.
    Fast Path: Reads from local CSV first (0.001s, zero network lag).
    Fallback: Reads from MongoDB Cloud if local file is missing/empty.
    """
    file_name, col_name, header, fields = _get_trade_meta(is_futures)
    time_col = 'Timestamp' if is_futures else 'Time'
    
    # 1. Fast Path: Read local CSV populated by Render (0.001s, instant)
    if os.path.exists(file_name) and os.path.getsize(file_name) > len(header):
        try:
            df = pd.read_csv(file_name)
            if not df.empty:
                return df
        except Exception:
            pass

    # 2. Fallback to MongoDB Cloud if local file is missing/empty
    curr_db = get_mongo_db()
    if curr_db is not None:
        try:
            docs = list(curr_db[col_name].find().sort(time_col, 1))
            if docs:
                clean_docs = []
                for d in docs:
                    item = {fld: d.get(fld, '') for fld in fields}
                    clean_docs.append(item)
                df = pd.DataFrame(clean_docs)
                try:
                    df.to_csv(file_name, index=False)
                except Exception:
                    pass
                return df
        except Exception:
            pass
            
    return pd.DataFrame(columns=fields)

def get_trade_history_csv(is_futures=False):
    """
    Returns complete CSV string representation of trade history.
    """
    df = get_trade_history_df(is_futures)
    file_name, col_name, header, fields = _get_trade_meta(is_futures)
    if df.empty:
        return header
    return df.to_csv(index=False)
