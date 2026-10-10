import os
import json
from pymongo import MongoClient
import certifi

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

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
        # Test connection
        client.server_info()
        db = client["trading_bot_db"]
        print("✅ MongoDB Connected Successfully!")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")
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
