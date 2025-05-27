from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
log_buffer = []

@app.route('/')
def index():
    return "✅ Webhook bot is live."

@app.route('/webhook', methods=['POST'])
def webhook():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        data = request.json
        log_buffer.append(f"[{timestamp}] ALERT RECEIVED: {data}")
        print("Received alert:", data)
        return jsonify({"status": "received"}), 200
    except Exception as e:
        log_buffer.append(f"[{timestamp}] ERROR PARSING ALERT: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/logs', methods=['GET'])
def logs():
    if not log_buffer:
        return "No logs yet."
    return "<pre>" + "\n".join(log_buffer[-100:]) + "</pre>"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
