#!/usr/bin/env python3
import requests
import json

def load_credentials(file_path):
    """Load credentials from a credentials.txt file."""
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

# Extract InfluxDB credentials
INFLUXDB_URL = credentials.get("INFLUXDB_URL")
INFLUXDB_TOKEN = credentials.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = credentials.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = credentials.get("INFLUXDB_BUCKET")

# Define the delete payload
payload = {
    "start": "1970-01-01T00:00:00Z",
    "stop": "2100-01-01T00:00:00Z",
    "predicate": "_measurement=\"acceleration\""
}

# Define the delete endpoint
url = f"{INFLUXDB_URL}/api/v2/delete?org={INFLUXDB_ORG}&bucket={INFLUXDB_BUCKET}"

# Set the headers
headers = {
    "Authorization": f"Token {INFLUXDB_TOKEN}",
    "Content-Type": "application/json"
}

# Send the delete request
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Check the response
if response.status_code == 204:
    print("Measurement 'acceleration' deleted successfully.")
elif response.status_code == 401:
    print("Unauthorized: Check your InfluxDB token.")
elif response.status_code == 404:
    print("Not Found: Check your InfluxDB URL or bucket.")
else:
    print(f"Failed to delete measurement. Status code: {response.status_code}")
    print(f"Response: {response.text}")