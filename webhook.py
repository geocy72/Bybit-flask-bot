from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# === API KEYS ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"

# === Bybit Client ===
session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# === Internal log buffer ===
log_buffer = []

# === Ρυθμίσεις ===
SL_PERCENT = 2.0  # Trailing Stop σε ποσοστό
MIN_QTY = 0.001

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

    try:
        action = data.get("action")
        symbol = data.get("symbol").upper()
        qty = float(data.get("qty"))
        order_type = data.get("type", "market").lower()
        side = "Buy" if action == "buy" else "Sell"

        if qty < MIN_QTY:
            raise ValueError(f"Order qty {qty} is below Bybit minimum {MIN_QTY}")

        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL → {result}")
            return jsonify({"status": "cancelled", "response": result}), 200

        # === Place Main Order ===
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] BYBIT RESPONSE: {order}")

        # === Get Entry Price
        ticker = session.get_tickers(category="linear", symbol=symbol)
        price = float(ticker["result"]["list"][0]["lastPrice"])

        # === Trailing Stop Setup
        trail_value = round(price * SL_PERCENT / 100, 4)
        opposite = "Sell" if side == "Buy" else "Buy"
        trigger_dir = 1 if side == "Buy" else 2

        trailing_stop_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=opposite,
            order_type="TrailingStopMarket",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            triggerDirection=trigger_dir,
            trailing_stop=trail_value
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP SET @ ΔΙΑΦΟΡΑ {trail_value} → {trailing_stop_order}")
        return jsonify({"status": "ok", "order": order}), 200

    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/logs', methods=['GET'])
def show_logs():
    if not log_buffer:
        return "No logs yet."
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

@app.route('/clear_logs', methods=['GET'])
def clear_logs():
    log_buffer.clear()
    return "🧹 Logs καθαρίστηκαν επιτυχώς!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
