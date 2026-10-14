import os
import json

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

client = None
db = None

if MONGO_URI and HAS_PYMONGO:
    # 1. Primary Attempt: Standard Atlas connection with official certifi CA bundle
    try:
        ca_file = certifi.where() if ('certifi' in globals() and certifi) else None
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000, tlsCAFile=ca_file)
        client.server_info()
        db = client["trading_bot_db"]
        print("✅ MongoDB Connected Successfully with Certifi TLS!")
    except Exception as e1:
        # 2. Secondary Attempt: Default TLS without custom CA
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            client.server_info()
            db = client["trading_bot_db"]
            print("✅ MongoDB Connected Successfully with Default TLS!")
        except Exception as e2:
            # 3. Tertiary Attempt: Fallback with tlsAllowInvalidCertificates
            try:
                client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000, tlsAllowInvalidCertificates=True)
                client.server_info()
                db = client["trading_bot_db"]
                print("✅ MongoDB Connected Successfully with Fallback TLS!")
            except Exception as e3:
                # Graceful Local Fallback: Never crash, store state in local JSON files
                print("ℹ️ MongoDB Cloud unreachable. Seamlessly using local state storage (dca_state.json, fo_state.json).")
                client = None
                db = None

def get_state(collection_name, default_val=None):
    if default_val is None:
        default_val = {}
        
    if db is not None:
        try:
            doc = db[collection_name].find_one({"_id": "state"})
            if doc and "data" in doc:
                return doc["data"]
            return default_val
        except Exception as e:
            pass
            
    # Fallback to local file
    file_path = f"{collection_name}.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except:
            pass
    return default_val

def save_state(collection_name, state_data):
    if db is not None:
        try:
            db[collection_name].update_one(
                {"_id": "state"},
                {"$set": {"data": state_data}},
                upsert=True
            )
        except Exception as e:
            pass
            
    # Always save local backup
    file_path = f"{collection_name}.json"
    try:
        with open(file_path, 'w') as f:
            json.dump(state_data, f, indent=4)
    except:
        pass
