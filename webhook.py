from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime
import math

app = Flask(__name__)

# === API KEYS ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"

session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

log_buffer = []

# === Ρυθμίσεις ===
TRAILING_PERCENT = 2.0
MIN_QTY = 0.001

# === Symbol precision (επεκτάσιμο) ===
symbol_precisions = {
    "BTCUSDT": 3,
    "ETHUSDT": 3,
    "SUIUSDT": 0
}

def round_qty(symbol, qty):
    precision = symbol_precisions.get(symbol.upper(), 3)
    return round(qty, precision)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

    try:
        action = data.get("action")
        symbol = data.get("symbol").upper()
        qty = float(data.get("qty"))
        qty = round_qty(symbol, qty)
        order_type = data.get("type", "market").lower()
        side = "Buy" if action == "buy" else "Sell"

        if qty < MIN_QTY:
            raise ValueError(f"Order qty {qty} is below Bybit minimum {MIN_QTY}")

        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL → {result}")
            return jsonify({"status": "cancelled", "response": result}), 200

        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] BYBIT RESPONSE: {order}")

        # === Trailing Stop ===
        opposite = "Sell" if side == "Buy" else "Buy"
        trail_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=opposite,
            order_type="TrailingStopMarket",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            trailing_stop=str(TRAILING_PERCENT)
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP @ -{TRAILING_PERCENT}% → {trail_order}")
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
