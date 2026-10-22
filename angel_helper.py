import os
import json
import pyotp
import time
import threading
from SmartApi import SmartConnect
import db_helper

class AngelOneEngine:
    def __init__(self):
        self.smart_api = None
        self.session_data = None
        self.last_login_time = 0
        self.last_login_attempt = 0
        self.cached_cash = 300.0
        self.last_cash_time = 0
        self._lock = threading.Lock()
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
            "SUZLON-EQ": {"token": "12018", "name": "SUZLON", "lotsize": "1"},
            "BEL-EQ": {"token": "383", "name": "BEL", "lotsize": "1"},
            "GAIL-EQ": {"token": "4717", "name": "GAIL", "lotsize": "1"},
            "PNB-EQ": {"token": "10666", "name": "PNB", "lotsize": "1"},
            "IRFC-EQ": {"token": "2029", "name": "IRFC", "lotsize": "1"},
            "MOTHERSON-EQ": {"token": "4204", "name": "MOTHERSON", "lotsize": "1"},
            "NHPC-EQ": {"token": "17400", "name": "NHPC", "lotsize": "1"}
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
        # Minimum 30s throttle on login attempts to avoid rate limits
        if time.time() - self.last_login_attempt < 30:
            return False, "Login throttled to prevent rate limits"
        self.last_login_attempt = time.time()

        creds = self._get_credentials()
        api_key = creds.get('api_key')
        client_code = creds.get('client_code')
        pin = creds.get('pin')
        totp_secret = creds.get('totp_secret')

        if not (api_key and client_code and pin and totp_secret):
            return False, "Angel One credentials missing"

        try:
            client = SmartConnect(api_key=api_key)
            totp = pyotp.TOTP(totp_secret).now()
            res = client.generateSession(client_code, pin, totp)
            if res and isinstance(res, dict) and res.get('status'):
                self.smart_api = client
                self.session_data = res.get('data', {})
                self.last_login_time = time.time()
                name = self.session_data.get('name', client_code)
                print(f"✅ Angel One Connected! Logged in as: {name} ({client_code})", flush=True)
                return True, self.session_data
            else:
                err = res.get('message', 'Login failed') if isinstance(res, dict) else str(res)
                return False, err
        except Exception as e:
            return False, str(e)

    def ensure_session(self):
        with self._lock:
            # Re-login only if no session or older than 12 hours (43200s)
            if self.smart_api and self.session_data and (time.time() - self.last_login_time < 43200):
                return True
            success, msg = self.login()
            if not success:
                # If we already had an active session, keep using it rather than failing
                if self.smart_api and self.session_data:
                    return True
                print(f"⚠️ Angel One Auto-Login Warning: {msg}", flush=True)
                return False
            return True

    def get_available_cash(self, force_refresh=False):
        # 1. Fast Cache Path (Return cached cash if fetched within 60 seconds)
        if not force_refresh and (time.time() - self.last_cash_time < 60) and self.cached_cash > 0:
            return self.cached_cash

        if not self.ensure_session():
            return self.cached_cash if self.cached_cash > 0 else 300.0

        with self._lock:
            # Re-check cache inside lock
            if not force_refresh and (time.time() - self.last_cash_time < 60) and self.cached_cash > 0:
                return self.cached_cash

            try:
                rms = self.smart_api.rmsLimit()
                if rms and isinstance(rms, dict) and rms.get('status') and 'data' in rms:
                    cash_val = float(rms['data'].get('availablecash', 0.0))
                    if cash_val > 0:
                        self.cached_cash = cash_val
                        self.last_cash_time = time.time()
                        return self.cached_cash
            except Exception as e:
                # Graceful fallback to cached cash on any transient rate limit
                pass
        return self.cached_cash if self.cached_cash > 0 else 300.0

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

        with self._lock:
            try:
                print(f"🚀 Placing Angel One {action} order: {quantity} shares of {tradingsymbol} ({product_type})...", flush=True)
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
