from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime
import math

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

log_buffer = []

# === Trailing Stop Settings ===
TRAILING_STOP_PERCENT = 2.0

def round_qty(symbol, qty):
    try:
        info = session.get_instruments_info(category="linear", symbol=symbol)
        step_size = float(info["result"]["list"][0]["lotSizeFilter"]["qtyStep"])
        precision = abs(int(round(math.log10(step_size))))
        return round(qty, precision)
    except Exception as e:
        log_buffer.append(f"[{datetime.utcnow()}] ERROR fetching step size: {e}")
        return qty

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

        action = data.get("action")
        symbol = data.get("symbol")
        raw_qty = float(data.get("qty"))
        qty = round_qty(symbol, raw_qty)
        order_type = data.get("type", "market").lower()
        side = "Buy" if action == "buy" else "Sell"

        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL → {result}")
            return jsonify({"status": "cancelled", "response": result}), 200

        # === Primary Order ===
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] BYBIT ORDER RESPONSE: {order}")

        # === Trailing Stop
        opposite = "Sell" if side == "Buy" else "Buy"
        trailing_stop = str(TRAILING_STOP_PERCENT)
        ts_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=opposite,
            order_type="TrailingStopMarket",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            trailing_stop=trailing_stop
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP -{TRAILING_STOP_PERCENT}% SET → {ts_order}")

        return jsonify({"status": "ok", "order": order, "trailing_stop": ts_order}), 200

    except Exception as e:
        error_msg = f"[{datetime.utcnow()}] ERROR: {str(e)}"
        log_buffer.append(error_msg)
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/logs', methods=['GET'])
def logs():
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

@app.route('/clear_logs', methods=['GET'])
def clear():
    log_buffer.clear()
    return "🧹 Logs cleared."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
