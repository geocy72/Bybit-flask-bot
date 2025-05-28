from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# === API KEYS ===
BYBIT_API_KEY = "ZRyWx3GREmB9LQET4u"
BYBIT_API_SECRET = "FzvPkH7tPuyDDZs0c7AAAskl1srtTvD4l8In"

# === Bybit Client ===
session = HTTP(
    testnet=False,  # True για testnet.bybit, False για live
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received alert:", data)

    action = data.get("action")
    symbol = data.get("symbol")
    qty = float(data.get("qty"))
    order_type = data.get("type", "market").lower()
    side = "Buy" if action == "buy" else "Sell"

    try:
        response = session.place_order(
            category="linear",  # 'spot' για spot market
            symbol=symbol,
            side=side,
            order_type=order_type.upper(),
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        print("Order response:", response)
        return jsonify({"status": "ok", "order": response}), 200
    except Exception as e:
        print("Error placing order:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
