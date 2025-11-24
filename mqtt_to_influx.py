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
            # Ignore empty lines and comments
            if line.strip() and not line.startswith("#"):
                # Remove "export" if it exists, then split into key-value
                line = line.replace("export ", "", 1)
                key, value = line.split("=", 1)
                credentials[key.strip()] = value.strip().strip('"')  # Remove quotes if present
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

# MQTT topics to subscribe to
TOPICS = {
    "antares/3960722352/28ee2d1d01160126": {"measurement": "temperature", "location": "Salon"},
    "antares/3960722352/28ee28d500160298": {"measurement": "temperature", "location": "Motor"},
    "antares/3960722352/accel": {"measurement": "acceleration"}
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

# Updated on_message function to calculate timestamps relative to the first measurement in each packet
def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        print(f"Received message from topic {topic}: {payload}")

        if topic in TOPICS:
            topic_config = TOPICS[topic]
            measurement = topic_config["measurement"]

            if measurement == "temperature":
                location = topic_config["location"]
                try:
                    temperature = float(payload)
                    write_to_influx(measurement, {"location": location}, {"value": temperature})
                except ValueError:
                    print(f"Invalid temperature value: {payload}")

            elif measurement == "acceleration":
                try:
                    accel_data = json.loads(payload)
                    if "data" in accel_data and len(accel_data["data"]) > 0:
                        # Get the current time as the base time in nanoseconds
                        current_time_ns = int(time.time() * 1e9)

                        # Use the timestamp of the first measurement as t0
                        t0 = accel_data["data"][0]["timestamp"]

                        for entry in accel_data["data"]:
                            relative_time_ns = int((entry["timestamp"] - t0) * 1e9)
                            influx_timestamp = current_time_ns + relative_time_ns

                            x = entry["x"]
                            y = entry["y"]
                            z = entry["z"]

                            write_to_influx(measurement, {}, {"x": x, "y": y, "z": z}, influx_timestamp)
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