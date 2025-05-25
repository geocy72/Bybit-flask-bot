from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime
from time import sleep

app = Flask(__name__)

# === API KEYS ===
BYBIT_API_KEY = "BbOKjCFtOMb6Gh01Gh"
BYBIT_API_SECRET = "GbTnD3cQC1J4vj7WFf8Ahd247AEA8GFzjOAA"

session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# === Log buffer ===
log_buffer = []

# === TP/SL settings ===
TP_PERCENT = 3.0
SL_PERCENT = 1.5

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")
    print("Received alert:", data)

    action = data.get("action")
    symbol = data.get("symbol")
    qty = float(data.get("qty"))
    order_type = data.get("type", "market").lower()
    side = "Buy" if action == "buy" else "Sell"

    try:
        # === Cancel all orders ===
        if action == "cancel_all":
            result = session.cancel_all_orders(category="linear", symbol=symbol)
            log_buffer.append(f"[{timestamp}] CANCEL ALL → {result}")
            return jsonify({"status": "cancelled", "response": result}), 200

        # === Open market order ===
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] BYBIT RESPONSE: {order}")
        print("Order response:", order)

        # === Get current price ===
        price = float(order['result'].get('orderPrice', 0))
        if price == 0:
            ticker = session.get_tickers(category="linear", symbol=symbol)
price = float(ticker["result"]["list"][0]["lastPrice"])


        # === Calculate TP & SL ===
        tp_price = round(price * (1 + TP_PERCENT / 100), 2) if side == "Buy" else round(price * (1 - TP_PERCENT / 100), 2)
        sl_price = round(price * (1 - SL_PERCENT / 100), 2) if side == "Buy" else round(price * (1 + SL_PERCENT / 100), 2)
        opposite = "Sell" if side == "Buy" else "Buy"

        # === Take Profit ===
        session.place_order(
            category="linear",
            symbol=symbol,
            side=opposite,
            order_type="Limit",
            price=tp_price,
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=True
        )

        # === Stop Loss ===
        session.place_order(
            category="linear",
            symbol=symbol,
            side=opposite,
            order_type="StopMarket",
            stop_px=sl_price,
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=True
        )

        log_buffer.append(f"[{timestamp}] TP set @ {tp_price}, SL set @ {sl_price}")
        return jsonify({"status": "ok", "order": order}), 200

    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        print("Error placing order:", str(e))
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
