from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime
import threading
import time
import os

app = Flask(__name__)

# === API KEYS ===
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "ZRyWx3GREmB9LQET4u")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In")

session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# === Settings ===
FIXED_QTY = 25
TRAILING_PERCENT = 2.0
TRIGGER_PERCENT = 1.0

log_buffer = []

# === Trailing Stop Monitoring ===
def monitor_price_and_set_trailing_stop(symbol, entry_price, side):
    target_price = entry_price * (1 + TRIGGER_PERCENT / 100)
    trailing_side = "Sell" if side == "Buy" else "Buy"

    while True:
        try:
            ticker = session.get_tickers(category="linear", symbol=symbol)
            last_price = float(ticker["result"]["list"][0]["lastPrice"])

            if (side == "Buy" and last_price >= target_price) or (side == "Sell" and last_price <= entry_price * (1 - TRIGGER_PERCENT / 100)):
                response = session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=trailing_side,
                    order_type="TrailingStopMarket",
                    qty=FIXED_QTY,
                    time_in_force="GoodTillCancel",
                    reduce_only=True,
                    trigger_by="LastPrice",
                    trailing_stop=str(TRAILING_PERCENT)
                )
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                log_buffer.append(f"[{timestamp}] TRAILING STOP ACTIVATED: {response}")
                break
        except Exception as e:
            log_buffer.append(f"[Monitor ERROR] {str(e)}")
            break

        time.sleep(5)

@app.route('/webhook', methods=['POST'])
def webhook():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        data = request.get_json(force=True)
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

        action = data.get("action")
        symbol = data.get("symbol")
        side = "Buy" if action == "buy" else "Sell"

        # Market order
        order_response = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=FIXED_QTY,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] PRIMARY ORDER RESPONSE: {order_response}")

        # Get entry price from ticker
        ticker = session.get_tickers(category="linear", symbol=symbol)
        entry_price = float(ticker["result"]["list"][0]["lastPrice"])

        # Start background monitor
        thread = threading.Thread(target=monitor_price_and_set_trailing_stop, args=(symbol, entry_price, side))
        thread.start()

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
