#!/usr/bin/env python3 
import os
import paho.mqtt.client as mqtt
import json
import time
import subprocess
import sys
import logging

print("Script execution started")

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
                if key != "WIFI_PWD" and key != "MQTT_PASS":
                    print(f"{key.strip()}: {value.strip().strip('\"')}")
                else:
                    print(f"{key.strip()}: {'*' * 8}")  # Mask sensitive info
            
                credentials[key.strip()] = value.strip().strip('"')  # Remove quotes if present
    return credentials

# Load credentials
credentials = load_credentials("credentials.txt")

# Extract MQTT and WiFi credentials
MQTT_USERNAME = credentials.get("MQTT_USER", "default_user")
MQTT_PASSWORD = credentials.get("MQTT_PASS", "default_password")
MQTT_BROKER = credentials.get("MQTT_URL", "mqtt://localhost").split("://")[1].split(":")[0]  # Extract hostname
MQTT_PORT = int(credentials.get("MQTT_URL", "mqtt://localhost:1883").split(":")[-1])  # Extract port
MQTT_TOPIC = "antares/3960722352/accel"  # Adjust if topic prefix differs

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 10  # Duration in seconds, default 10
PLOT_RESOLUTION = sys.argv[2] if len(sys.argv) > 2 else "1920x1080"  # Default resolution

# Parse resolution
try:
    width, height = map(int, PLOT_RESOLUTION.lower().split('x'))
except ValueError:
    print("Invalid resolution format. Use WIDTHxHEIGHT (e.g., 1920x1080).")
    sys.exit(1)

data = []

def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
        for point in payload['data']:
            data.append((point['timestamp'], point['x'], point['y'], point['z']))  # Use timestamp from MQTT message
    except json.JSONDecodeError:
        print("Invalid JSON received")

logging.basicConfig(level=logging.DEBUG)
print(f"MQTT_BROKER: {MQTT_BROKER}, MQTT_PORT: {MQTT_PORT}, MQTT_TOPIC: {MQTT_TOPIC}")
client = mqtt.Client()
client.enable_logger()
client.on_message = on_message
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(MQTT_BROKER, MQTT_PORT)
client.subscribe(MQTT_TOPIC)
client.loop_start()

print(f"Collecting data for {DURATION} seconds...")
time.sleep(DURATION)
client.loop_stop()

if not data:
    print("No data collected")
    sys.exit(1)

# Write data to file
with open('accel.dat', 'w') as f:
    for t, x, y, z in data:
        f.write(f"{t} {x} {y} {z}\n")

# Create gnuplot script
gnuplot_script = f"""
set terminal png size {width},{height}
set output 'accel.png'
set title 'Acceleration over Time'
set xlabel 'Time (s)'
set ylabel 'Acceleration (m/s²)'
set grid
plot 'accel.dat' using 1:2 with lines title 'X', \
     'accel.dat' using 1:3 with lines title 'Y', \
     'accel.dat' using 1:4 with lines title 'Z'
"""

with open('plot.gp', 'w') as f:
    f.write(gnuplot_script)

# Run gnuplot
subprocess.run(['gnuplot', 'plot.gp'])
print("Plot saved as accel.png")

# Display the plot
subprocess.run(['xdg-open', 'accel.png'])  # Open the plot using the default image viewer