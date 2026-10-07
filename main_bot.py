import threading
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import binance_bot
import futures_bot

print("Starting 24/7 Trading Bot Backend Worker (Render Web Service)...")

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<h1>Trading Bot is Running 24/7!</h1>".encode('utf-8'))

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"Web service started on port {port}")
    server.serve_forever()

def run_spot():
    while True:
        try:
            print("Starting Spot Bot...")
            binance_bot.run_bot_loop()
        except Exception as e:
            print(f"Spot Bot Error: {e}")
            time.sleep(10)

def run_futures():
    while True:
        try:
            print("Starting Futures Bot...")
            futures_bot.run_futures_bot()
        except Exception as e:
            print(f"Futures Bot Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_spot, daemon=True)
    t1.start()
    
    t2 = threading.Thread(target=run_futures, daemon=True)
    t2.start()
    
    run_dummy_server()
