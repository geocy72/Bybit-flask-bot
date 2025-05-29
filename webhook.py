from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# === BYBIT LIVE API KEYS ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"

session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# === LOGGING ===
log_buffer = []

# === CONFIG ===
TRAILING_STOP_USD = 2.0  # $ trailing distance
FIXED_QTY = 25.0
MIN_QTY = 0.001

# === GET STEP SIZE ===
def get_step_size(symbol):
    try:
        info = session.get_instruments_info(category="linear", symbol=symbol)
        return float(info["result"]["list"][0]["lotSizeFilter"]["qtyStep"])
    except Exception as e:
        log_buffer.append(f"[ERROR] Could not get step size: {e}")
        return 0.01

def round_qty(qty, step):
    precision = abs(str(step)[::-1].find('.'))
    return round(qty, precision)

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

        if FIXED_QTY < MIN_QTY:
            raise ValueError(f"Order qty {FIXED_QTY} is below Bybit minimum {MIN_QTY}")

        step = get_step_size(symbol)
        qty_rounded = round_qty(FIXED_QTY, step)

        # MAIN ORDER
        main_order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=qty_rounded,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] MAIN ORDER → {main_order}")

        # TRAILING STOP ORDER
        trailing_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell" if side == "Buy" else "Buy",
            order_type="Market",
            qty=qty_rounded,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            trailing_stop=str(TRAILING_STOP_USD)
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP SET → {trailing_order}")

        return jsonify({"status": "ok", "order": main_order}), 200

    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/', methods=['GET'])
def status():
    return "✅ Webhook Bot is running."

@app.route('/logs', methods=['GET'])
def show_logs():
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

@app.route('/clear_logs', methods=['GET'])
def clear_logs():
    log_buffer.clear()
    return "🧹 Logs cleared."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
