import os
import json
import websocket
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
KAFKA_TOPIC = "raw-trades"
KAFKA_BROKER = "localhost:9092"
SYMBOLS = ["AAPL", "GOOGL", "MSFT", "AMZN"]

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

## Send each trade individually to Kafka

def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "trade":
        for trade in data.get("data", []):
            producer.send(KAFKA_TOPIC, trade)
            print(f"Sent : {trade}")

## Debug info / general logging

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    for symbol in SYMBOLS:
        ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
    print(f"Subscribed to: {SYMBOLS}")

# Main call

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()