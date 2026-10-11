import threading
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import binance_bot
import futures_bot

print("Starting 24/7 Trading Bot Backend Worker (Render Web Service)...", flush=True)

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        import json
        import os
        
        # 🔄 REMOTE ZERO RESET TRIGGER
        if self.path == '/reset':
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                # 1. Reset DCA State
                with open("dca_state.json", "w") as f:
                    json.dump({}, f)
                # 2. Reset Futures State
                with open("fo_state.json", "w") as f:
                    json.dump({}, f)
                # 3. Reset Trades Log
                with open("trades_log.csv", "w") as f:
                    f.write("Time,Symbol,Action,Price,Shares,Profit\n")
                # 4. Reset MongoDB if helper exists
                try:
                    import db_helper
                    db_helper.save_state('dca_state', {})
                    db_helper.save_state('fo_state', {})
                except:
                    pass
                msg = {"status": "SUCCESS", "message": "పోర్ట్‌ఫోలియో మరియు ట్రేడ్ హిస్టరీ పూర్తిగా జీరో చేసాము! AI కి కొత్తగా ₹50,000 క్యాపిటల్ కేటాయించబడింది. 🔥"}
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
            out = {"status": "Trading Bot is running 24/7 on Render...", "MongoDB_Link": "Failed - Showing Local Data"}
            
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

if __name__ == "__main__":
    t1 = threading.Thread(target=run_spot, daemon=True)
    t1.start()
    
    t2 = threading.Thread(target=run_futures, daemon=True)
    t2.start()
    
    run_dummy_server()
