import os
import json
import time
import hmac
import hashlib
import struct
import base64
import requests
import db_helper

# Cached Session
_angel_session = {
    "jwtToken": None,
    "refreshToken": None,
    "feedToken": None,
    "expires_at": 0
}

# Pre-populated Token Map for Top NSE Bluechip Stocks (Angel One Scrip Tokens)
NSE_SYMBOL_TOKENS = {
    "RELIANCE": {"token": "2885", "tradingsymbol": "RELIANCE-EQ"},
    "RELIANCE.NS": {"token": "2885", "tradingsymbol": "RELIANCE-EQ"},
    "HDFCBANK": {"token": "1333", "tradingsymbol": "HDFCBANK-EQ"},
    "HDFCBANK.NS": {"token": "1333", "tradingsymbol": "HDFCBANK-EQ"},
    "ICICIBANK": {"token": "4963", "tradingsymbol": "ICICIBANK-EQ"},
    "ICICIBANK.NS": {"token": "4963", "tradingsymbol": "ICICIBANK-EQ"},
    "INFY": {"token": "1594", "tradingsymbol": "INFY-EQ"},
    "INFY.NS": {"token": "1594", "tradingsymbol": "INFY-EQ"},
    "TCS": {"token": "11536", "tradingsymbol": "TCS-EQ"},
    "TCS.NS": {"token": "11536", "tradingsymbol": "TCS-EQ"},
    "SBIN": {"token": "3045", "tradingsymbol": "SBIN-EQ"},
    "SBIN.NS": {"token": "3045", "tradingsymbol": "SBIN-EQ"},
    "BHARTIARTL": {"token": "10604", "tradingsymbol": "BHARTIARTL-EQ"},
    "BHARTIARTL.NS": {"token": "10604", "tradingsymbol": "BHARTIARTL-EQ"},
    "ITC": {"token": "1660", "tradingsymbol": "ITC-EQ"},
    "ITC.NS": {"token": "1660", "tradingsymbol": "ITC-EQ"},
    "TMCV": {"token": "3456", "tradingsymbol": "TATAMOTORS-EQ"},
    "TMCV.NS": {"token": "3456", "tradingsymbol": "TATAMOTORS-EQ"},
    "TATAMOTORS": {"token": "3456", "tradingsymbol": "TATAMOTORS-EQ"},
    "TATAMOTORS.NS": {"token": "3456", "tradingsymbol": "TATAMOTORS-EQ"},
    "LT": {"token": "11483", "tradingsymbol": "LT-EQ"},
    "LT.NS": {"token": "11483", "tradingsymbol": "LT-EQ"},
    "BAJFINANCE": {"token": "317", "tradingsymbol": "BAJFINANCE-EQ"},
    "BAJFINANCE.NS": {"token": "317", "tradingsymbol": "BAJFINANCE-EQ"},
    "TATASTEEL": {"token": "3499", "tradingsymbol": "TATASTEEL-EQ"},
    "TATASTEEL.NS": {"token": "3499", "tradingsymbol": "TATASTEEL-EQ"},
    "AXISBANK": {"token": "5900", "tradingsymbol": "AXISBANK-EQ"},
    "AXISBANK.NS": {"token": "5900", "tradingsymbol": "AXISBANK-EQ"},
    "MARUTI": {"token": "10999", "tradingsymbol": "MARUTI-EQ"},
    "MARUTI.NS": {"token": "10999", "tradingsymbol": "MARUTI-EQ"},
    "SUNPHARMA": {"token": "3351", "tradingsymbol": "SUNPHARMA-EQ"},
    "SUNPHARMA.NS": {"token": "3351", "tradingsymbol": "SUNPHARMA-EQ"},
    "KOTAKBANK": {"token": "1922", "tradingsymbol": "KOTAKBANK-EQ"},
    "KOTAKBANK.NS": {"token": "1922", "tradingsymbol": "KOTAKBANK-EQ"},
    "TITAN": {"token": "3506", "tradingsymbol": "TITAN-EQ"},
    "TITAN.NS": {"token": "3506", "tradingsymbol": "TITAN-EQ"},
    "POWERGRID": {"token": "14977", "tradingsymbol": "POWERGRID-EQ"},
    "POWERGRID.NS": {"token": "14977", "tradingsymbol": "POWERGRID-EQ"},
    "NTPC": {"token": "11630", "tradingsymbol": "NTPC-EQ"},
    "NTPC.NS": {"token": "11630", "tradingsymbol": "NTPC-EQ"},
    "ETERNAL": {"token": "5097", "tradingsymbol": "ZOMATO-EQ"},
    "ETERNAL.NS": {"token": "5097", "tradingsymbol": "ZOMATO-EQ"},
    "ZOMATO": {"token": "5097", "tradingsymbol": "ZOMATO-EQ"},
    "ZOMATO.NS": {"token": "5097", "tradingsymbol": "ZOMATO-EQ"},
    "SUZLON": {"token": "7712", "tradingsymbol": "SUZLON-EQ"},
    "SUZLON.NS": {"token": "7712", "tradingsymbol": "SUZLON-EQ"},
    "TATAPOWER": {"token": "3426", "tradingsymbol": "TATAPOWER-EQ"},
    "TATAPOWER.NS": {"token": "3426", "tradingsymbol": "TATAPOWER-EQ"},
    "WIPRO": {"token": "3787", "tradingsymbol": "WIPRO-EQ"},
    "WIPRO.NS": {"token": "3787", "tradingsymbol": "WIPRO-EQ"},
    "ADANIENT": {"token": "25", "tradingsymbol": "ADANIENT-EQ"},
    "ADANIENT.NS": {"token": "25", "tradingsymbol": "ADANIENT-EQ"},
    "ADANIPORTS": {"token": "15083", "tradingsymbol": "ADANIPORTS-EQ"},
    "ADANIPORTS.NS": {"token": "15083", "tradingsymbol": "ADANIPORTS-EQ"},
    "COALINDIA": {"token": "20374", "tradingsymbol": "COALINDIA-EQ"},
    "COALINDIA.NS": {"token": "20374", "tradingsymbol": "COALINDIA-EQ"},
    "ONGC": {"token": "2475", "tradingsymbol": "ONGC-EQ"},
    "ONGC.NS": {"token": "2475", "tradingsymbol": "ONGC-EQ"},
    "ASIANPAINT": {"token": "236", "tradingsymbol": "ASIANPAINT-EQ"},
    "ASIANPAINT.NS": {"token": "236", "tradingsymbol": "ASIANPAINT-EQ"},
    "HINDUNILVR": {"token": "1394", "tradingsymbol": "HINDUNILVR-EQ"},
    "HINDUNILVR.NS": {"token": "1394", "tradingsymbol": "HINDUNILVR-EQ"},
    "JSWSTEEL": {"token": "11723", "tradingsymbol": "JSWSTEEL-EQ"},
    "JSWSTEEL.NS": {"token": "11723", "tradingsymbol": "JSWSTEEL-EQ"},
    "HCLTECH": {"token": "7229", "tradingsymbol": "HCLTECH-EQ"},
    "HCLTECH.NS": {"token": "7229", "tradingsymbol": "HCLTECH-EQ"},
    "BPCL": {"token": "526", "tradingsymbol": "BPCL-EQ"},
    "BPCL.NS": {"token": "526", "tradingsymbol": "BPCL-EQ"},
    "BEL": {"token": "383", "tradingsymbol": "BEL-EQ"},
    "BEL.NS": {"token": "383", "tradingsymbol": "BEL-EQ"},
    "HAL": {"token": "2303", "tradingsymbol": "HAL-EQ"},
    "HAL.NS": {"token": "2303", "tradingsymbol": "HAL-EQ"}
}

def generate_totp(secret):
    """
    Generates dynamic 6-digit TOTP from secret token.
    Uses pyotp if installed; otherwise standard library RFC 6238 HMAC-SHA1.
    """
    if not secret or not str(secret).strip():
        return ""
    
    clean_secret = str(secret).strip().replace(" ", "").upper()
    try:
        import pyotp
        return pyotp.TOTP(clean_secret).now()
    except Exception:
        pass

    try:
        # Standard library fallback (zero external dependencies)
        key = base64.b32decode(clean_secret, True)
        counter = int(time.time()) // 30
        msg = struct.pack('>Q', counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[19] & 15
        h_num = struct.unpack('>I', h[o:o+4])[0] & 0x7fffffff
        return str(h_num % 1000000).zfill(6)
    except Exception:
        return ""

def load_angel_config():
    """
    Loads Angel One SmartAPI credentials with multi-tier fallback:
    1. Local angel_config.json
    2. Cloud MongoDB Atlas 'angel_config' collection
    3. Environment Variables
    """
    config = {
        "client_code": "AABZ864543",
        "pin": "1122",
        "api_key": "eVNyHHxR",
        "totp_secret": "MDXMIH4K46DYD77VFGFT4FO6YU",
        "product_type": "INTRADAY",
        "is_live": True
    }

    # 1. Local JSON
    if os.path.exists("angel_config.json"):
        try:
            with open("angel_config.json", "r") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    config.update(saved)
        except Exception:
            pass

    # 2. MongoDB Atlas (Cloud Sync)
    try:
        cloud_cfg = db_helper.get_state('angel_config', {}) or db_helper.get_state('angel_credentials', {})
        if cloud_cfg and isinstance(cloud_cfg, dict):
            for k, v in cloud_cfg.items():
                if v and not config.get(k):
                    config[k] = v
    except Exception:
        pass

    # 3. Environment Variables
    if not config["client_code"]:
        config["client_code"] = os.environ.get("ANGEL_CLIENT_CODE", "")
    if not config["pin"]:
        config["pin"] = os.environ.get("ANGEL_PIN", "")
    if not config["api_key"]:
        config["api_key"] = os.environ.get("ANGEL_API_KEY", "")
    if not config["totp_secret"]:
        config["totp_secret"] = os.environ.get("ANGEL_TOTP_SECRET", "")

    return config

def save_angel_config(client_code, pin=None, api_key=None, totp_secret=None, product_type="INTRADAY", is_live=True):
    """
    Saves Angel One credentials to both local file AND MongoDB Atlas.
    Guarantees synchronization between Streamlit Dashboard and Render master server.
    Accepts either a single dictionary or positional parameters.
    """
    if isinstance(client_code, dict):
        d = client_code
        client_code = d.get("client_code", "")
        pin = d.get("pin", "")
        api_key = d.get("api_key", "")
        totp_secret = d.get("totp_secret", "")
        product_type = d.get("product_type", "INTRADAY")
        is_live = d.get("is_live", True)

    cfg = {
        "client_code": str(client_code or "").strip(),
        "pin": str(pin or "").strip(),
        "api_key": str(api_key or "").strip(),
        "totp_secret": str(totp_secret or "").strip(),
        "product_type": product_type,
        "is_live": is_live,
        "updated_at": db_helper.get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 1. Local File
    try:
        with open("angel_config.json", "w") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        pass

    # 2. Cloud MongoDB Atlas
    try:
        db_helper.save_state('angel_config', cfg)
    except Exception:
        pass

    # Reset cached session so it re-authenticates with new credentials
    global _angel_session
    _angel_session["jwtToken"] = None
    _angel_session["expires_at"] = 0
    return True

def get_session():
    """
    Authenticates with Angel One SmartAPI and returns active JWT token.
    Caches token in-memory for 12 hours.
    """
    global _angel_session
    now = time.time()
    if _angel_session["jwtToken"] and now < _angel_session["expires_at"]:
        return _angel_session["jwtToken"], _angel_session.get("feedToken")

    cfg = load_angel_config()
    client_code = cfg.get("client_code", "").strip()
    pin = cfg.get("pin", "").strip()
    api_key = cfg.get("api_key", "").strip()
    totp_secret = cfg.get("totp_secret", "").strip()

    if not (client_code and pin and api_key and totp_secret):
        return None, "Missing Angel One credentials (Client Code, PIN, API Key, or TOTP Secret)"

    totp_code = generate_totp(totp_secret)
    if not totp_code:
        return None, "Failed to generate dynamic TOTP. Check TOTP Secret Key."

    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/loginByPassword"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "106.193.147.98",
        "X-MACAddress": "fe80::216e:6507:4b9c:9045",
        "X-PrivateKey": api_key
    }
    payload = {
        "clientcode": client_code,
        "password": pin,
        "totp": totp_code
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        data = resp.json()
        if data.get("status") is True and "data" in data and "jwtToken" in data["data"]:
            token = data["data"]["jwtToken"]
            feed = data["data"].get("feedToken")
            # Angel One tokens are valid for the trading day (~16 hours)
            _angel_session["jwtToken"] = token
            _angel_session["feedToken"] = feed
            _angel_session["refreshToken"] = data["data"].get("refreshToken")
            _angel_session["expires_at"] = now + (12 * 3600)
            return token, feed
        else:
            msg = data.get("message", "Login failed")
            err_code = data.get("errorcode", "")
            return None, f"Angel One Login Failed [{err_code}]: {msg}"
    except Exception as e:
        return None, f"Angel One Connection Error: {e}"

def get_angel_funds():
    """
    Calls Angel One /getRMS endpoint to fetch real available cash, net balance, and margins.
    Returns:
        dict: {"availablecash": float, "net": float, "collateral": float, "status": bool, "error": str}
    """
    cfg = load_angel_config()
    api_key = cfg.get("api_key", "").strip()
    token, err = get_session()
    if not token:
        return {"status": False, "error": err, "availablecash": 0.0, "net": 0.0}

    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS"
    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "106.193.147.98",
        "X-MACAddress": "fe80::216e:6507:4b9c:9045",
        "X-PrivateKey": api_key,
        "Authorization": auth_header
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        data = resp.json()
        if data.get("status") is True and "data" in data:
            d = data["data"]
            avail = float(d.get("availablecash", 0.0) or 0.0)
            net = float(d.get("net", avail) or avail)
            coll = float(d.get("collateral", 0.0) or 0.0)
            return {
                "status": True,
                "availablecash": avail,
                "net": net,
                "collateral": coll,
                "m2munrealized": float(d.get("m2munrealized", 0.0) or 0.0),
                "m2mrealized": float(d.get("m2mrealized", 0.0) or 0.0),
                "raw": d
            }
        else:
            return {"status": False, "error": data.get("message", "Could not fetch RMS"), "availablecash": 0.0, "net": 0.0}
    except Exception as e:
        return {"status": False, "error": str(e), "availablecash": 0.0, "net": 0.0}

def get_angel_profile():
    """Fetches user client name, email, client code from Angel One."""
    cfg = load_angel_config()
    api_key = cfg.get("api_key", "").strip()
    token, err = get_session()
    if not token:
        return {"status": False, "error": err}

    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "106.193.147.98",
        "X-MACAddress": "fe80::216e:6507:4b9c:9045",
        "X-PrivateKey": api_key,
        "Authorization": auth_header
    }
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        data = resp.json()
        if data.get("status") is True and "data" in data:
            return {"status": True, "data": data["data"]}
        return {"status": False, "error": data.get("message", "Profile fetch failed")}
    except Exception as e:
        return {"status": False, "error": str(e)}

def get_symbol_token(symbol):
    """
    Maps symbol (e.g. 'RELIANCE.NS', 'TMCV.NS', 'HDFCBANK.NS') to Angel One token & tradingsymbol.
    """
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").replace("-USD", "").upper()
    
    # Check pre-populated bluechips map
    if clean_sym in NSE_SYMBOL_TOKENS:
        return NSE_SYMBOL_TOKENS[clean_sym]["tradingsymbol"], NSE_SYMBOL_TOKENS[clean_sym]["token"]
    if symbol in NSE_SYMBOL_TOKENS:
        return NSE_SYMBOL_TOKENS[symbol]["tradingsymbol"], NSE_SYMBOL_TOKENS[symbol]["token"]

    # Default fallback tradingsymbol
    ts = f"{clean_sym}-EQ"
    return ts, ""

def execute_angel_order(action, symbol, quantity, order_type="MARKET", product_type="INTRADAY"):
    """
    Executes a real live order on Angel One SmartAPI (NSE Equity).
    action: 'BUY' or 'SELL'
    quantity: int/float
    """
    cfg = load_angel_config()
    api_key = cfg.get("api_key", "").strip()
    token, err = get_session()
    if not token:
        return False, f"Angel One Authentication Error: {err}"

    tradingsymbol, symboltoken = get_symbol_token(symbol)
    if not symboltoken:
        return False, f"Missing Angel One symbol token for {symbol}"

    prod = cfg.get("product_type", product_type) or "INTRADAY"
    try:
        qty_int = int(round(float(quantity))) if quantity else 1
    except Exception:
        qty_int = 1
    if qty_int <= 0:
        qty_int = 1

    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/placeOrder"
    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "106.193.147.98",
        "X-MACAddress": "fe80::216e:6507:4b9c:9045",
        "X-PrivateKey": api_key,
        "Authorization": auth_header
    }
    payload = {
        "variety": "NORMAL",
        "tradingsymbol": tradingsymbol,
        "symboltoken": symboltoken,
        "transactiontype": action.upper(),
        "exchange": "NSE",
        "ordertype": order_type.upper(),
        "producttype": prod.upper(),
        "duration": "DAY",
        "price": "0",
        "squareoff": "0",
        "stoploss": "0",
        "quantity": str(qty_int)
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        data = resp.json()
        if data.get("status") is True and "data" in data and "orderid" in data["data"]:
            order_id = data["data"]["orderid"]
            return True, order_id
        else:
            msg = data.get("message", "Order rejected")
            err_code = data.get("errorcode", "")
            return False, f"Angel One Order Error [{err_code}]: {msg}"
    except Exception as e:
        return False, f"Angel One Order Exception: {e}"

def is_connected():
    """Tests Angel One connectivity and credentials validity."""
    token, err = get_session()
    if not token:
        return False, err
    funds = get_angel_funds()
    if funds.get("status"):
        return True, f"Connected (Available Cash: ₹{funds.get('availablecash', 0.0):,.2f})"
    return False, funds.get("error", "RMS funds check failed")
