
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# === BYBIT API KEYS (LIVE) ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"

session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

log_buffer = []

# === Ρυθμίσεις ===
FIXED_QTY = 25

@app.route('/webhook', methods=['POST'])
def webhook():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        data = request.get_json(force=True)
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

        action = data.get("action")
        symbol = data.get("symbol")
        order_type = data.get("type", "market").lower()
        side = "Buy" if action == "buy" else "Sell"

        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL → {result}")
            return jsonify({"status": "cancelled", "response": result}), 200

        # Κύρια εντολή
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=FIXED_QTY,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] BYBIT ORDER RESPONSE: {order}")
        return jsonify({"status": "ok", "order": order}), 200

    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/', methods=['GET'])
def status():
    return "✅ Webhook bot is running!"

@app.route('/logs', methods=['GET'])
def show_logs():
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

@app.route('/clear_logs', methods=['GET'])
def clear_logs():
    log_buffer.clear()
    return "🧹 Logs καθαρίστηκαν."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
