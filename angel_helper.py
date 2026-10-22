import os
import json
import pyotp
import time
from SmartApi import SmartConnect
import db_helper

class AngelOneEngine:
    def __init__(self):
        self.smart_api = None
        self.session_data = None
        self.last_login_time = 0
        self.tokens_map = self._load_tokens_map()

    def _load_tokens_map(self):
        token_file = os.path.join(os.path.dirname(__file__), 'angel_tokens.json')
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "HDFCBANK-EQ": {"token": "1333", "name": "HDFCBANK", "lotsize": "1"},
            "TCS-EQ": {"token": "11536", "name": "TCS", "lotsize": "1"},
            "INFY-EQ": {"token": "1594", "name": "INFY", "lotsize": "1"},
            "ITC-EQ": {"token": "1660", "name": "ITC", "lotsize": "1"},
            "ICICIBANK-EQ": {"token": "4963", "name": "ICICIBANK", "lotsize": "1"},
            "SBIN-EQ": {"token": "3045", "name": "SBIN", "lotsize": "1"},
            "RELIANCE-EQ": {"token": "2885", "name": "RELIANCE", "lotsize": "1"},
            "TATASTEEL-EQ": {"token": "3499", "name": "TATASTEEL", "lotsize": "1"},
            "ONGC-EQ": {"token": "2475", "name": "ONGC", "lotsize": "1"},
            "IOC-EQ": {"token": "1624", "name": "IOC", "lotsize": "1"},
            "SUZLON-EQ": {"token": "12018", "name": "SUZLON", "lotsize": "1"}
        }

    def _get_credentials(self):
        # 1. Try local file
        cred_file = os.path.join(os.path.dirname(__file__), 'angel_credentials.json')
        if os.path.exists(cred_file):
            try:
                with open(cred_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        # 2. Try MongoDB
        return db_helper.get_state('angel_credentials', {})

    def login(self):
        creds = self._get_credentials()
        api_key = creds.get('api_key')
        client_code = creds.get('client_code')
        pin = creds.get('pin')
        totp_secret = creds.get('totp_secret')

        if not (api_key and client_code and pin and totp_secret):
            return False, "Angel One credentials missing"

        try:
            self.smart_api = SmartConnect(api_key=api_key)
            totp = pyotp.TOTP(totp_secret).now()
            res = self.smart_api.generateSession(client_code, pin, totp)
            if res and res.get('status'):
                self.session_data = res.get('data', {})
                self.last_login_time = time.time()
                name = self.session_data.get('name', client_code)
                print(f"✅ Angel One Connected! Logged in as: {name} ({client_code})", flush=True)
                return True, self.session_data
            else:
                err = res.get('message', 'Login failed')
                return False, err
        except Exception as e:
            return False, str(e)

    def ensure_session(self):
        # Re-login if no session or older than 12 hours
        if not self.smart_api or (time.time() - self.last_login_time > 43200):
            success, msg = self.login()
            if not success:
                print(f"⚠️ Angel One Auto-Login Warning: {msg}", flush=True)
                return False
        return True

    def get_available_cash(self):
        if not self.ensure_session():
            return 0.0
        try:
            rms = self.smart_api.rmsLimit()
            if rms and rms.get('status') and 'data' in rms:
                return float(rms['data'].get('availablecash', 0.0))
        except Exception as e:
            print(f"Error fetching Angel One cash: {e}", flush=True)
        return 0.0

    def execute_order(self, action, nse_symbol, quantity, product_type="INTRADAY"):
        """
        action: 'BUY' or 'SELL'
        nse_symbol: e.g. 'ITC.NS' or 'HDFCBANK.NS'
        quantity: number of shares (int)
        product_type: 'INTRADAY' (MIS) or 'DELIVERY' (CNC)
        """
        if not self.ensure_session():
            return False, "Not authenticated with Angel One"

        clean_sym = nse_symbol.replace('.NS', '').replace('.BO', '').upper()
        tradingsymbol = f"{clean_sym}-EQ"
        token_info = self.tokens_map.get(tradingsymbol)

        if not token_info:
            return False, f"Token not found for {tradingsymbol}"

        symbol_token = str(token_info.get('token'))

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": tradingsymbol,
            "symboltoken": symbol_token,
            "transactiontype": action.upper(),
            "exchange": "NSE",
            "ordertype": "MARKET",
            "producttype": product_type.upper(),
            "duration": "DAY",
            "quantity": str(int(quantity))
        }

        try:
            print(f"🚀 Placing Angel One {action} order: {quantity} shares of {tradingsymbol}...", flush=True)
            order_res = self.smart_api.placeOrder(order_params)
            if order_res and isinstance(order_res, dict) and order_res.get('status'):
                order_id = order_res.get('data', {}).get('orderid', 'SUCCESS')
                print(f"✅ Angel One {action} Executed Successfully! Order ID: {order_id}", flush=True)
                return True, order_id
            else:
                err_msg = order_res.get('message', str(order_res)) if isinstance(order_res, dict) else str(order_res)
                print(f"⚠️ Angel One Order Warning: {err_msg}", flush=True)
                return False, err_msg
        except Exception as e:
            return False, str(e)

# Singleton Instance
angel_engine = AngelOneEngine()
