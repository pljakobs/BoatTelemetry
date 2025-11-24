// --- Accelerometer Analysis Functions ---
#include <math.h>
#include <vector>
#include <algorithm>
#include <ArduinoJson.h>

#include <SmingCore.h>
#include <Libraries/OneWire/OneWire.h>
#include <DallasTemperature.h>
#include "../include/telemetry.h"
#include "esp_system.h"
#include "esp_pm.h"

#include "driver/rtc_io.h"

#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>

#define ONE_WIRE_BUS 6 // GPIO6 for ESP32-C3
#define TEMPERATURE_PRECISION 9

#define SCL_PIN 7
#define SDA_PIN 8

#define BUFFER_SIZE 2000

#ifndef WIFI_SSID
#define WIFI_SSID "Antares"
#define WIFI_PWD "meinwlangehoertmir"
#endif

TelemetryClient* telemetryClient = nullptr;


Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);

// Setup a oneWire instance to communicate with any OneWire devices
OneWire oneWire(ONE_WIRE_BUS);

// Pass our oneWire reference to Dallas Temperature
DallasTemperature sensors(&oneWire);
DeviceAddress sensorAddress;
SimpleTimer procTimer;
SimpleTimer accelTimer;

// Global variables
float normalX_global = 0, normalY_global = 0, normalZ_global = 0;
std::vector<std::array<float, 4>> accelBuffer;  // Buffer for {timestamp, x, y, z} objects


// Calculate horizontal acceleration magnitude from X and Y axes
[[ maybe_unused ]] float calcHorizontalAccel(float ax, float ay) {
    return sqrtf(ax * ax + ay * ay);
}

// Calculate amplitude (peak-to-peak) from a buffer of Z values
[[ maybe_unused ]] float calcAmplitude(const std::vector<float>& zBuffer) {
    if (zBuffer.empty()) return 0.0f;
    auto [minIt, maxIt] = std::minmax_element(zBuffer.begin(), zBuffer.end());
    return *maxIt - *minIt;
}

[[ maybe_unused ]] float kalmanUpdate(float measurement) {
    static float kalmanX = 0.0f;  // Estimated state
    static float kalmanP = 1.0f;  // Estimate error covariance
    static float kalmanQ = 0.1f;  // Process noise
    static float kalmanR = 0.1f;  // Measurement noise
    
    // Prediction
    float x_pred = kalmanX;
    float p_pred = kalmanP + kalmanQ;
    
    // Update
    float k = p_pred / (p_pred + kalmanR);
    kalmanX = x_pred + k * (measurement - x_pred);
    kalmanP = (1 - k) * p_pred;
    
    return kalmanX;
}

void calibrateNormalVector(int samples = 500, int delayMs = 20) {
    Serial.println("Calibrating normal vector... Keep sensor still!");
    
    std::vector<float> xVals, yVals, zVals;
    for (int i = 0; i < samples; ++i) {
        sensors_event_t event;
        if (accel.getEvent(&event)) {
            xVals.push_back(event.acceleration.x);
            yVals.push_back(event.acceleration.y);
            zVals.push_back(event.acceleration.z);
        }
        delay(delayMs);
    }
    
    if (xVals.empty()) return;
    
    normalX_global = std::accumulate(xVals.begin(), xVals.end(), 0.0f) / samples;
    normalY_global = std::accumulate(yVals.begin(), yVals.end(), 0.0f) / samples;
    normalZ_global = std::accumulate(zVals.begin(), zVals.end(), 0.0f) / samples;
    float magnitude = sqrtf(normalX_global * normalX_global + normalY_global * normalY_global + normalZ_global * normalZ_global);
    
    Serial.printf("Normal Vector: (%.2f, %.2f, %.2f) m/s² | Magnitude: %.2f\n", normalX_global, normalY_global, normalZ_global, magnitude);
}

void printAddress(DeviceAddress deviceAddress)
{
    for (uint8_t i = 0; i < 8; i++) {
        if (deviceAddress[i] < 16) Serial.print("0");
        Serial.print(deviceAddress[i], HEX);
    }
}

void printTemperature(DeviceAddress deviceAddress)
{
    float tempC = sensors.getTempC(deviceAddress);
    if (tempC == DEVICE_DISCONNECTED_C) {
        Serial.println("Error: Could not read temperature data");
        return;
    }
    Serial.print("Temp C: ");
    Serial.print(tempC);
}

void printData(DeviceAddress deviceAddress)
{
    Serial.print("Device Address: ");
    printAddress(deviceAddress);
    Serial.print(" ");
    printTemperature(deviceAddress);
    Serial.println();
}

void readAccelDataRaw() {
    // Read raw data from ADXL345 (assumes I2C is set up)
    Wire.beginTransmission(0x53);
    Wire.write(0x32);  // DATAX0 register
    Wire.endTransmission(false);
    Wire.requestFrom(0x53, 6);
    
    if (Wire.available() == 6) {
        int16_t xRaw = Wire.read() | (Wire.read() << 8);
        int16_t yRaw = Wire.read() | (Wire.read() << 8);
        int16_t zRaw = Wire.read() | (Wire.read() << 8);
        
        // Manual scaling for 2G range: 256 LSB/G * 9.81 m/s²/G
        float scale = (1.0f / 256.0f) * 9.81f;  // 0.0383 m/s² per LSB
        float x = xRaw * scale;
        float y = yRaw * scale;
        float z = zRaw * scale;
        
        Serial.printf("Raw: X=%d Y=%d Z=%d | Scaled: X=%.2f Y=%.2f Z=%.2f\n", xRaw, yRaw, zRaw, x, y, z);
    } else {
        Serial.println("Failed to read raw data");
    }
}

float calcVariance(const std::vector<float>& buffer) {
    if (buffer.empty()) return 0.0f;
    float mean = std::accumulate(buffer.begin(), buffer.end(), 0.0f) / buffer.size();
    float variance = 0.0f;
    for (float val : buffer) {
        variance += (val - mean) * (val - mean);
    }
    return variance / buffer.size();
}

[[ maybe_unused ]] float calcPeriod(const std::vector<float>& zBuffer, float sampleRate) {
    if (zBuffer.size() < 3) return 0.0f;
    std::vector<size_t> peaks;
    float minPeakHeight = 0.05f;  // Minimum peak height (tune as needed)
    for (size_t i = 1; i < zBuffer.size() - 1; ++i) {
        if (zBuffer[i] > zBuffer[i-1] && zBuffer[i] > zBuffer[i+1] && zBuffer[i] > minPeakHeight) {
            peaks.push_back(i);
        }
    }
    if (peaks.size() < 2) return 0.0f;
    // Calculate average period between peaks
    float totalPeriod = 0.0f;
    for (size_t i = 1; i < peaks.size(); ++i) {
        totalPeriod += (peaks[i] - peaks[i-1]);
    }
    float avgSamples = totalPeriod / (peaks.size() - 1);
    return avgSamples / sampleRate;
}

void readAccelData()
{
    static int sampleCounter = 0;
    sampleCounter++;
    
    sensors_event_t event;
    if (!accel.getEvent(&event)) return;
    
    // Collect raw data as {timestamp, x, y, z} object
    float timestamp = millis() / 1000.0f;  // Convert milliseconds to seconds
    accelBuffer.push_back({timestamp, event.acceleration.x, event.acceleration.y, event.acceleration.z});

    // Every second (50 samples at 20ms), publish to MQTT
    if (sampleCounter >= 50) {
        StaticJsonDocument<4096> doc;  // Adjust size as needed
        JsonArray dataArray = doc.createNestedArray("data");
        
        for (const auto& point : accelBuffer) {
            JsonObject obj = dataArray.createNestedObject();
            obj["timestamp"] = point[0];  // Add timestamp
            obj["x"] = point[1];
            obj["y"] = point[2];
            obj["z"] = point[3];
        }
        
        telemetryClient->publish("accel", doc);
        
        // Clear buffer
        accelBuffer.clear();
        sampleCounter = 0;
    }
}

void readData()
{
    static int reading_count = 0;
    reading_count++;
    Serial.printf("\n=== Reading #%d ===\n", reading_count);

    Serial.print("Requesting temperatures...");
    sensors.requestTemperatures();
    Serial.println("DONE");

    int sensorCount = sensors.getDeviceCount();
    Serial.printf("Sensor count: %d\n", sensorCount);

    for (int i = 0; i < sensorCount; i++) {
        DeviceAddress addr;
        telemetryClient->publish("sensorCount",String(sensorCount));
        if (sensors.getAddress(addr, i)) {
            printData(addr);
            // Telemetry example
            float tempC = sensors.getTempC(addr);
            if (telemetryClient && telemetryClient->isRunning()) {
                String sensorIdStr;
                for (uint8_t j = 0; j < 8; j++) {
                    if (addr[j] < 16) sensorIdStr += "0";
                    sensorIdStr += String(addr[j], HEX);
                }
                telemetryClient->publish(sensorIdStr,String(tempC,2));
                String logMsg = "Sensor " + String(i+1) + ": " + String(tempC, 2) + "°C";
                telemetryClient->log(logMsg);
            }
        } else {
            Serial.printf("Unable to find address for Device %d\n", i);
        }
    }
}


void init() {
    #ifdef UART_ID_SERIAL_USB_JTAG
        Serial.setPort(UART_ID_SERIAL_USB_JTAG);
    #endif

    Serial.begin(SERIAL_BAUD_RATE);
    Serial.systemDebugOutput(true);
    delay(500);

    // Use preprocessor macros for WiFi and MQTT credentials
    const char* wifiSSID = WIFI_SSID;
    const char* wifiPassword = WIFI_PWD;
    const char* mqttServer = MQTT_URL;
    const char* mqttUser = MQTT_USER;
    const char* mqttPass = MQTT_PASS;

    Serial.println("Initializing WiFi...");
    WifiStation.enable(true);
    WifiStation.config(wifiSSID, wifiPassword);

    WifiEvents.onStationGotIP([=](IpAddress ip, IpAddress netmask, IpAddress gateway) {
        Serial.printf("WiFi connected! IP: %s\n", ip.toString().c_str());

        // Initialize telemetry client
        telemetryClient = new TelemetryClient(mqttServer, mqttUser, mqttPass, APP_ID);
        telemetryClient->start();
        Serial.println("Telemetry client started");

        // Start timers
        procTimer.initializeMs<10000>(readData).start();
        accelTimer.initializeMs<20>(readAccelData).start();
    });

    WifiEvents.onStationDisconnect([](const String& ssid, MacAddress bssid, WifiDisconnectReason reason) {
        Serial.printf("WiFi disconnected from %s (reason %d)\n", ssid.c_str(), reason);
        Serial.println("Attempting to reconnect...");
        WifiStation.connect();
    });

    WifiStation.connect();
}