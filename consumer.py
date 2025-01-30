from kafka.consumer import KafkaConsumer
from kafka.producer import KafkaProducer
import json
from collections import defaultdict
from datetime import datetime

# Kafka Configuration
KAFKA_BROKER = "localhost:29092"
SOURCE_TOPIC = "user-login"
DEST_TOPIC = "processed-user-login"
MAX_MESSAGES = 10  # Set the maximum number of messages to process
TIMEOUT_MS = 5000  # Stop consumer after 5 seconds of inactivity

# Kafka Consumer
consumer = KafkaConsumer(
    SOURCE_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    consumer_timeout_ms=TIMEOUT_MS,  # Stop consuming after timeout
)

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
)

print("Consumer is listening...")

count = 0
platform_usage = defaultdict(int)
version_usage = defaultdict(int)
login_times = []

try:
    for message in consumer:
        try:
            data = message.value

            # Validate required fields
            required_fields = ["user_id", "app_version", "device_type", "timestamp"]
            if not all(field in data for field in required_fields):
                print(f"Skipping message due to missing fields: {data}")
                continue

            # Aggregation: Count device type and app version usage
            platform_usage[data["device_type"]] += 1
            version_usage[data["app_version"]] += 1

            # Transform timestamp into human-readable format
            try:
                formatted_time = datetime.utcfromtimestamp(int(data["timestamp"]))
                data["formatted_timestamp"] = formatted_time.strftime('%Y-%m-%d %H:%M:%S')
                login_times.append(formatted_time)
            except ValueError:
                print(f"Invalid timestamp format: {data['timestamp']}")
                continue

            # Example processing: Filtering users with Android devices and app version > 3.0
            if data.get("device_type") == "android" and float(data.get("app_version", 0)) > 3.0:
                transformed_data = {
                    "user_id": data["user_id"],
                    "app_version": data["app_version"],
                    "device_type": data["device_type"],
                    "formatted_timestamp": data["formatted_timestamp"],
                }

                # Send to new Kafka topic
                producer.send(DEST_TOPIC, value=transformed_data)
                print(f"Processed and sent: {transformed_data}")

                count += 1
                if count >= MAX_MESSAGES:
                    print("Reached maximum message limit. Stopping consumer...")
                    break  # Exit after processing MAX_MESSAGES
        except Exception as e:
            print(f"Error processing message: {e}")
            continue
except Exception as e:
    print(f"Consumer encountered an error: {e}")

# Print insights
print("\n--- Insights ---")
print("Device Type Usage:")
for device, count in platform_usage.items():
    print(f"{device}: {count} users")

print("\nApp Version Usage:")
for version, count in version_usage.items():
    print(f"Version {version}: {count} users")

# Calculate peak login times if enough data
if login_times:
    peak_hour = max(set([t.hour for t in login_times]), key=[t.hour for t in login_times].count)
    print(f"\nPeak Login Hour: {peak_hour}:00")

# Close the consumer and producer
consumer.close()
producer.close()
print("Consumer stopped.")
