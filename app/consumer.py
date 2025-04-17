
from faststream import FastStream
from faststream.confluent import KafkaBroker

from config import config

print(config.db.kafka_url)
broker = KafkaBroker(config.db.kafka_url)

app = FastStream(broker)

@broker.subscriber("postgres.public.statuses")
async def on_status(event):
    print(event)

# import sys
# from confluent_kafka import Consumer, KafkaError
# import json

# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# def process_debezium_event(msg):
#     try:
#         # Deserialize the byte string to a Python dictionary
#         event = json.loads(msg.value().decode('utf-8'))
#     except Exception as e:
#         print(f"Error parsing message: {e}")
#         return

#     # Debezium event structure example:
#     # {
#     #   "before": { ... },  # Data before change (for updates/deletes)
#     #   "after": { ... },   # Data after change (for inserts/updates)
#     #   "op": "c",          # Operation: 'c' (create), 'u' (update), 'd' (delete)
#     #   "ts_ms": 1620000000,
#     #   "source": { ... }
#     # }

#     payload = event.get('payload', event)
    
#     op = payload.get('op')

#     if op == 'c':
#         print(f"New record inserted: {payload['after']}")
#     elif op == 'u':
#         print(f"Record updated. New data: {payload['after']}")
#     elif op == 'd':
#         print(f"Record deleted: {payload['before']}")
#     else:
#         print(f"Unhandled operation: {op}")

# conf = {
#     'bootstrap.servers': 'localhost:29092',
#     'group.id': 'debezium-consumer-group',
#     'auto.offset.reset': 'earliest'
# }

# consumer = Consumer(conf)

# consumer.subscribe([
#     'postgres.public.statuses'
# ])

# try:
#     while True:
#         msg = consumer.poll(timeout=1.0)
#         if msg is None:
#             continue
#         if msg.error():
#             if msg.error().code() == KafkaError._PARTITION_EOF:
#                 continue
#             else:
#                 print(f"Error: {msg.error()}")
#                 break
#         process_debezium_event(msg)
# except KeyboardInterrupt:
#     pass
# finally:
#     consumer.close()