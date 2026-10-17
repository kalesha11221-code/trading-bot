import threading
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import binance_bot
import futures_bot
import db_helper

print("Starting 24/7 Trading Bot Backend Worker (Render Web Service)...", flush=True)
try:
    db_helper.sync_cloud_to_local(is_futures=False)
    db_helper.sync_cloud_to_local(is_futures=True)
except Exception as e:
    print(f"Startup cloud restore info: {e}", flush=True)

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        import json
        import os
        
        # 🔄 REMOTE ZERO RESET TRIGGER (Futures, Spot, or All)
        if self.path in ('/reset', '/reset_all'):
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                db_helper.reset_trade_history(is_futures=False)
                db_helper.reset_trade_history(is_futures=True)
                db_helper.save_state('dca_state', {})
                db_helper.save_state('fo_state', {})
                msg = {"status": "SUCCESS", "message": "All trade history and states reset successfully!"}
                self.wfile.write(json.dumps(msg, ensure_ascii=False, indent=4).encode('utf-8'))
                return
            except Exception as e:
                self.wfile.write(json.dumps({"status": "ERROR", "error": str(e)}).encode('utf-8'))
                return

        if self.path == '/reset_futures':
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                db_helper.reset_trade_history(is_futures=True)
                db_helper.save_state('fo_state', {})
                msg = {"status": "SUCCESS", "message": "Futures trade history reset successfully!"}
                self.wfile.write(json.dumps(msg, ensure_ascii=False, indent=4).encode('utf-8'))
                return
            except Exception as e:
                self.wfile.write(json.dumps({"status": "ERROR", "error": str(e)}).encode('utf-8'))
                return

        if self.path == '/reset_spot':
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                db_helper.reset_trade_history(is_futures=False)
                db_helper.save_state('dca_state', {})
                msg = {"status": "SUCCESS", "message": "Spot trade history reset successfully!"}
                self.wfile.write(json.dumps(msg, ensure_ascii=False, indent=4).encode('utf-8'))
                return
            except Exception as e:
                self.wfile.write(json.dumps({"status": "ERROR", "error": str(e)}).encode('utf-8'))
                return

        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        try:
            import json
            import os
            import db_helper
            
            db_conn = db_helper.get_mongo_db()
            mongo_link = "Connected - Cloud Persistent Storage (Zero Data Loss)" if db_conn is not None else "Local Storage Fallback"
            out = {"status": "Trading Bot is running 24/7 on Render...", "MongoDB_Link": mongo_link}
            
            if os.path.exists("bot_heartbeat.json"):
                with open("bot_heartbeat.json", "r") as f:
                    out["heartbeat"] = json.load(f)
            else:
                out["heartbeat"] = "No heartbeat file found locally"
                
            if os.path.exists("dca_state.json"):
                with open("dca_state.json", "r") as f:
                    out["dca_state"] = json.load(f)
                    
            if os.path.exists("fo_state.json"):
                with open("fo_state.json", "r") as f:
                    out["fo_state"] = json.load(f)
                    
            if os.path.exists("live_scan_status.json"):
                with open("live_scan_status.json", "r") as f:
                    out["scan_status"] = json.load(f)
                    
            # Always return complete, authoritative persistent trade logs
            out["trades_log"] = db_helper.get_trade_history_csv(is_futures=False)
            out["fo_trades_log"] = db_helper.get_trade_history_csv(is_futures=True)
                    
            self.wfile.write(json.dumps(out, indent=4).encode('utf-8'))
        except Exception as e:
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"Web service started on port {port}", flush=True)
    server.serve_forever()

def run_spot():
    while True:
        try:
            print("Starting Spot Bot...", flush=True)
            binance_bot.run_bot_loop()
        except Exception as e:
            print(f"Spot Bot Error: {e}", flush=True)
            time.sleep(10)

def run_futures():
    while True:
        try:
            print("Starting Futures Bot...", flush=True)
            futures_bot.run_futures_bot()
        except Exception as e:
            print(f"Futures Bot Error: {e}", flush=True)
            time.sleep(10)

def keep_alive_worker():
    """24/7 Anti-Sleep Keep-Alive Engine: Pings Render and Streamlit every 2 minutes"""
    import requests
    print("Anti-Sleep Keep-Alive Engine Started (24/7 Ping)...", flush=True)
    time.sleep(15)
    while True:
        try:
            # 1. Ping Render itself to prevent sleep
            requests.get("https://trading-bot-leaw.onrender.com", timeout=15)
        except Exception:
            pass
        try:
            # 2. Ping Streamlit Cloud dashboard to prevent inactivity sleep
            requests.get("https://trading-bot-doea47tp79egvycwajfnjq.streamlit.app", timeout=15)
        except Exception:
            pass
        time.sleep(120)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_spot, daemon=True)
    t1.start()
    
    t2 = threading.Thread(target=run_futures, daemon=True)
    t2.start()
    
    t3 = threading.Thread(target=keep_alive_worker, daemon=True)
    t3.start()
    
    run_dummy_server()

