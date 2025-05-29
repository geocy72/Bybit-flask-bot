from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# === LIVE BYBIT KEYS ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"
session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# === Configuration ===
FIXED_QTY = 25  # Always use 25 units
TRAILING_PERCENT = 2.0  # Trailing stop loss in percent
log_buffer = []

@app.route('/webhook', methods=['POST'])
def webhook():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        data = request.get_json(force=True)
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

        action = data.get("action")
        symbol = data.get("symbol")
        side = "Buy" if action == "buy" else "Sell"

        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL RESPONSE: {result}")
            return jsonify({"status": "cancelled", "response": result}), 200

        # Primary market order
        response = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="MARKET",
            qty=FIXED_QTY,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] PRIMARY ORDER RESPONSE: {response}")

        # Trailing stop order in opposite direction
        opposite = "Sell" if side == "Buy" else "Buy"
        trailing_response = session.place_order(
            category="linear",
            symbol=symbol,
            side=opposite,
            order_type="Market",
            qty=FIXED_QTY,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            trailing_stop=str(TRAILING_PERCENT)
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP ORDER RESPONSE: {trailing_response}")

        return jsonify({"status": "ok", "order": response}), 200

    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/', methods=['GET'])
def home():
    return "✅ Webhook Bot is running"

@app.route('/logs', methods=['GET'])
def logs():
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
