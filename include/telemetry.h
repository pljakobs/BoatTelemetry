#pragma once
#include <ArduinoJson.h>
#include <Network/MqttClient.h> // Include for MqttClient, TcpClient, and mqtt_message_t

#define TELEMETRY_URL_MAX_SIZE 128
#define TELEMETRY_USER_MAX_SIZE 64
#define TELEMETRY_PASS_MAX_SIZE 64
#define TELEMETRY_CHIPID_MAX_SIZE 16
#define TELEMETRY_ID_MAX_SIZE 32
#define TELEMETRY_TOPIC_MAX_SIZE 128

class TelemetryClient {
public:
    TelemetryClient(String mqtt_server, String mqtt_user, String mqtt_pass, String node_id);
    virtual ~TelemetryClient();

    void start();
    void stop();
    bool stat(const JsonDocument& doc);
    bool log(const char* message);
    bool log(const String& message);
    bool publish(const char* topic, const JsonDocument& doc);
    bool publish(const String& topic, const JsonDocument& doc);
    bool publish(const char* topic, const char* payload);
    bool publish(const String& topic, const String& payload);
    void connect(const char* debugServer, const char* debugUser, const char* debugPass);
    void connect(const String& debugServer, const String& debugUser, const String& debugPass);
    void reconnect();
    bool isRunning() const { return _isRunning; }
private:
    void onComplete(TcpClient& client, bool success);
    int onConnected(MqttClient& client, mqtt_message_t* message);
    int onMessageReceived(MqttClient& client, mqtt_message_t* message);
    void buildTopic(const char* suffix, char* dest, size_t size);

    char _telemetryURL[TELEMETRY_URL_MAX_SIZE];
    char _telemetryUser[TELEMETRY_USER_MAX_SIZE];
    char _telemetryPass[TELEMETRY_PASS_MAX_SIZE];
    char _nodeId[TELEMETRY_ID_MAX_SIZE];
    char _chipId[TELEMETRY_CHIPID_MAX_SIZE];
    
    bool _isRunning = false;
    MqttClient* mqtt = nullptr;
};