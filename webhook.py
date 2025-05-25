from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# === API KEYS ===
BYBIT_API_KEY = "BbOKjCFtOMb6Gh01Gh"
BYBIT_API_SECRET = "GbTnD3cQC1J4vj7WFf8Ahd247AEA8GFzjOAA"

# === Bybit Client ===
session = HTTP(
    testnet=True,  # True για testnet, False για live
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# === Internal log buffer ===
log_buffer = []

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
        response = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        log_buffer.append(f"[{timestamp}] BYBIT RESPONSE: {response}")
        print("Order response:", response)
        return jsonify({"status": "ok", "order": response}), 200
    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR: {str(e)}")
        print("Error placing order:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/logs', methods=['GET'])
def show_logs():
    if not log_buffer:
        return "No logs yet."
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

