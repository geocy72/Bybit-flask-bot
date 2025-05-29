
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# === API KEYS (live) ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"

session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

log_buffer = []

TRAILING_PERCENT = 2.0
FIXED_QTY = 25.0
MIN_QTY = 0.001

@app.route('/webhook', methods=['POST'])
def webhook():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        data = request.get_json(force=True)
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

        action = data.get("action")
        symbol = data.get("symbol").upper()
        order_type = data.get("type", "market").lower()
        side = "Buy" if action == "buy" else "Sell"

        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL → {result}")
            return jsonify({"status": "cancelled", "response": result}), 200

        # Πριν ανοίξουμε νέα θέση, κλείνουμε την αντίθετη αν υπάρχει
        positions = session.get_positions(category="linear", symbol=symbol)["result"]["list"]
        for pos in positions:
            size = float(pos["size"])
            pos_side = pos["side"]
            if size > 0 and ((pos_side == "Buy" and side == "Sell") or (pos_side == "Sell" and side == "Buy")):
                close_side = "Sell" if pos_side == "Buy" else "Buy"
                session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=close_side,
                    order_type="Market",
                    qty=round(size, 2),
                    reduce_only=True,
                    time_in_force="GoodTillCancel"
                )
                log_buffer.append(f"[{timestamp}] CLOSED OPPOSITE POSITION: {pos_side} {size}")

        # Νέα εντολή με σταθερή ποσότητα
        main_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=FIXED_QTY,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] BYBIT ORDER RESPONSE: {main_order}")

        # Trailing Stop
        trailing_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell" if side == "Buy" else "Buy",
            order_type="Market",
            qty=FIXED_QTY,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            trailing_stop=str(TRAILING_PERCENT)
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP @ -{TRAILING_PERCENT}%")

        return jsonify({"status": "ok", "order": main_order}), 200

    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/', methods=['GET'])
def home():
    return "✅ Webhook is running!"

@app.route('/logs', methods=['GET'])
def show_logs():
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

@app.route('/clear_logs', methods=['GET'])
def clear_logs():
    log_buffer.clear()
    return "🧹 Logs cleared."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
