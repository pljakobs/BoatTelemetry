#!/usr/bin/env python3
import os
import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
import time

# Function to load credentials from credentials.txt
def load_credentials(file_path):
    credentials = {}
    with open(file_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                line = line.replace("export ", "", 1)
                key, value = line.split("=", 1)
                credentials[key.strip()] = value.strip().strip('"')
    return credentials

# Load credentials
credentials = load_credentials("credentials.txt")

# Extract MQTT and InfluxDB credentials
MQTT_URL = credentials.get("MQTT_URL")
MQTT_USER = credentials.get("MQTT_USER")
MQTT_PASS = credentials.get("MQTT_PASS")
INFLUXDB_URL = credentials.get("INFLUXDB_URL")
INFLUXDB_BUCKET = credentials.get("INFLUXDB_BUCKET")
INFLUXDB_TOKEN = credentials.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = credentials.get("INFLUXDB_ORG")

# Load topics configuration from topics.json
with open("topics.json", "r") as f:
    TOPICS_CONFIG = json.load(f)

# Flatten topics for subscription
TOPICS = {}
for env, env_data in TOPICS_CONFIG["environments"].items():
    for loc, loc_data in env_data["locations"].items():
        for topic, sensor_data in loc_data["sensors"].items():
            TOPICS[topic] = {
                "measurement": sensor_data["measurement"],
                "tags": {
                    "environment": env,
                    "location": loc
                }
            }

# Initialize InfluxDB client
influx_client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

write_api = influx_client.write_api()

# Debugging: Print the data being written to InfluxDB
def write_to_influx(measurement, tags, fields, time=None):
    point = {
        "measurement": measurement,
        "tags": tags,
        "fields": fields
    }
    if time:
        point["time"] = time
    print(f"Writing to InfluxDB: {point}")  # Debugging line
    write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
    print(f"Written to InfluxDB: {point}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        for topic in TOPICS.keys():
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        print(f"Received message from topic {topic}: {payload}")

        if topic in TOPICS:
            topic_config = TOPICS[topic]
            measurement = topic_config["measurement"]
            tags = topic_config["tags"]

            if measurement == "acceleration":
                try:
                    accel_data = json.loads(payload)
                    if "data" in accel_data and len(accel_data["data"]) > 0:
                        current_time_ns = int(time.time() * 1e9)
                        t0 = accel_data["data"][0]["timestamp"]

                        for entry in accel_data["data"]:
                            relative_time_ns = int((entry["timestamp"] - t0) * 1e9)
                            influx_timestamp = current_time_ns + relative_time_ns

                            x = float(entry.get("x", 0))
                            y = float(entry.get("y", 0))
                            z = float(entry.get("z", 0))
                            pitch = float(entry.get("pitch", 0))
                            roll = float(entry.get("roll", 0))
                            yaw = float(entry.get("yaw", 0))

                            write_to_influx(
                                measurement,
                                tags,
                                {"x": x, "y": y, "z": z, "pitch": pitch, "roll": roll, "yaw": yaw},
                                influx_timestamp
                            )
                except (ValueError, KeyError, json.JSONDecodeError) as e:
                    print(f"Error processing acceleration data: {e}")
    except Exception as e:
        print(f"Unhandled exception in on_message: {e}")

# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Connect to MQTT broker
mqtt_client.connect(MQTT_URL.split("//")[-1].split(":")[0], int(MQTT_URL.split(":")[-1]))

# Start the MQTT loop
mqtt_client.loop_forever()