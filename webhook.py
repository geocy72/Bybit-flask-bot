from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# === API KEYS ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"

session = HTTP(
    testnet=False,  # False για live
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# === ROUNDING PRECISION PER SYMBOL ===
symbol_precision = {
    "BTCUSDT": 3,
    "ETHUSDT": 3,
    "SUIUSDT": 2,
    "SOLUSDT": 2,
    "DOGEUSDT": 0,
    "XRPUSDT": 0,
    # Πρόσθεσε όσα άλλα χρειάζεσαι
}

TRAILING_STOP_PERCENT = 2.0
log_buffer = []

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")

        action = data.get("action")
        symbol = data.get("symbol").upper()
        qty_raw = float(data.get("qty"))
        order_type = data.get("type", "market").lower()
        side = "Buy" if action == "buy" else "Sell"

        # Cancel all
        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL: {result}")
            return jsonify({"status": "cancelled"}), 200

        # Στρογγυλοποίηση με βάση το symbol
        decimals = symbol_precision.get(symbol, 3)
        qty = round(qty_raw, decimals)

        # Άνοιγμα κύριας θέσης
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="MARKET",
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] ORDER: {order}")

        # Trailing Stop στο αντίθετο side
        trailing_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell" if side == "Buy" else "Buy",
            order_type="TrailingStopMarket",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            trigger_by="LastPrice",
            trailing_stop=str(TRAILING_STOP_PERCENT)
        )
        log_buffer.append(f"[{timestamp}] TRAILING STOP: {trailing_order}")

        return jsonify({"status": "ok", "order": order}), 200

    except Exception as e:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/logs', methods=['GET'])
def logs():
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

@app.route('/clear_logs', methods=['GET'])
def clear_logs():
    log_buffer.clear()
    return "🧹 Logs καθαρίστηκαν!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
