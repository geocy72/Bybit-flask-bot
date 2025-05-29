from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime
import os

app = Flask(__name__)

# === LIVE BYBIT API KEYS (Φυλάσσονται σε περιβαλλοντικές μεταβλητές για ασφάλεια) ===
BYBIT_API_KEY = os.getenv("ZRyWx3GREmB9LQET4u")
BYBIT_API_SECRET = os.getenv("FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In")

if not BYBIT_API_KEY or not BYBIT_API_SECRET:
    raise ValueError("Bybit API Key or Secret not set in environment variables!")

# Δημιουργία Bybit session
session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# Λήψη επιτρεπόμενων συμβόλων από το Bybit
def get_available_symbols():
    try:
        response = session.get_instruments_info(category="linear")
        symbols = [instrument["symbol"] for instrument in response["result"]["list"]]
        return set(symbols)
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return set()

AVAILABLE_SYMBOLS = get_available_symbols()
TRAILING_PERCENT = 2.0  # Trailing Stop στο -2%
log_buffer = []

@app.route('/webhook', methods=['POST'])
def webhook():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        data = request.get_json(force=True)
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

        action = data.get("action")
        symbol = data.get("symbol")
        qty = float(data.get("quantity"))  # Δυναμικό ποσό από το webhook payload

        if not symbol or not qty or not action:
            raise ValueError("Missing required parameters: action, symbol, or quantity")

        # Έλεγχος αν το σύμβολο είναι έγκυρο
        if symbol not in AVAILABLE_SYMBOLS:
            raise ValueError(f"Invalid symbol: {symbol}. Not supported by Bybit.")

        side = "Buy" if action.lower() == "buy" else "Sell"
        if action.lower() not in ["buy", "sell"]:
            raise ValueError(f"Invalid action: {action}. Must be 'buy' or 'sell'.")

        # Market Entry Order
        order_response = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] PRIMARY ORDER RESPONSE: {order_response}")

        # Trailing Stop στο -2% (αντίθετη κατεύθυνση)
        trailing_side = "Sell" if side == "Buy" else "Buy"
        trailing_response = session.place_order(
            category="linear",
            symbol=symbol,
            side=trailing_side,
            order_type="TrailingStopMarket",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            trailing_stop=str(TRAILING_PERCENT)
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP RESPONSE: {trailing_response}")

        return jsonify({"status": "ok", "order": order_response}), 200

    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/', methods=['GET'])
def status():
    return "✅ Webhook Bot is running!"

@app.route('/logs', methods=['GET'])
def logs():
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
