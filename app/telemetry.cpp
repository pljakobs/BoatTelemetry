#include "telemetry.h"
TelemetryClient::TelemetryClient(String mqtt_server, String mqtt_user, String mqtt_pass, String node_id) {

	strncpy(_telemetryURL, mqtt_server.c_str(), TELEMETRY_URL_MAX_SIZE);
    _telemetryURL[TELEMETRY_URL_MAX_SIZE - 1] = '\0';
	strncpy(_telemetryUser, mqtt_user.c_str(), TELEMETRY_USER_MAX_SIZE);
    _telemetryUser[TELEMETRY_USER_MAX_SIZE - 1] = '\0';
	strncpy(_telemetryPass, mqtt_pass.c_str(), TELEMETRY_PASS_MAX_SIZE);
    _telemetryPass[TELEMETRY_PASS_MAX_SIZE - 1] = '\0';
	snprintf(_chipId, TELEMETRY_CHIPID_MAX_SIZE, "%u", system_get_chip_id());
	mqtt = new MqttClient();
	snprintf(_nodeId, TELEMETRY_ID_MAX_SIZE, "%s/%s", node_id.c_str(), _chipId);
}

TelemetryClient::~TelemetryClient() {
	if (mqtt) {
		delete mqtt;
		mqtt = nullptr;
	}
}

void TelemetryClient::start() {	
	connect(_telemetryURL, _telemetryUser, _telemetryPass);
}

void TelemetryClient::stop() {
	_isRunning = false;
}

void TelemetryClient::connect(const char* telemetryURL, const char* telemetryUser, const char* telemetryPass) {
	// Connect to public MQTT server (example: test.mosquitto.org)

	if(strlen(telemetryURL)>0 && strlen(telemetryUser)>0 && strlen(telemetryPass)>0){
		// Build URL: mqtt://user:pass@server:port
		char url[256];
        snprintf(url, sizeof(url), "mqtt://%s:%s@%s", telemetryUser, telemetryPass, telemetryURL);
        debug_i("Telemetry MQTT connecting to %s", url);
        char clientId[64];
        snprintf(clientId, sizeof(clientId), "telemetry_client_%s", _chipId);
		mqtt->connect(url, clientId);
		mqtt->setCompleteDelegate([this](TcpClient& client, bool success) { this->onComplete(client, success); });
		mqtt->setConnectedHandler([this](MqttClient& client, mqtt_message_t* message) { return this->onConnected(client, message); });
		mqtt->setMessageHandler([this](MqttClient& client, mqtt_message_t* message) { return this->onMessageReceived(client, message); });
	} else {
		Serial.println("Telemetry MQTT not configured properly");
	}
}

void TelemetryClient::connect(const String& telemetryURL, const String& telemetryUser, const String& telemetryPass) {
    connect(telemetryURL.c_str(), telemetryUser.c_str(), telemetryPass.c_str());
}

void TelemetryClient::reconnect() {
    stop();
    delay(1000); // brief delay before reconnecting
    connect(_telemetryURL, _telemetryUser, _telemetryPass);
 }

void TelemetryClient::onComplete(TcpClient& client, bool success) {
	if (!success) {
		Serial.println("Telemetry MQTT connection failed");
		_isRunning = false;
	}
}

int TelemetryClient::onConnected(MqttClient& client, mqtt_message_t* message) {
	Serial.println("Telemetry MQTT connected");
    _isRunning = true;
	return 0;
}

int TelemetryClient::onMessageReceived(MqttClient& client, mqtt_message_t* message) {
	// Not used for publishing only
	return 0;
}

void TelemetryClient::buildTopic(const char* suffix, char* dest, size_t size) {
    snprintf(dest, size, "%s/%s", _nodeId, suffix);
	debug_i("Telemetry MQTT built topic: %s", dest);
    dest[size - 1] = '\0';
}

bool TelemetryClient::publish(const char* topic, const JsonDocument& doc) {
	debug_i("Telemetry MQTT publish called");
    if (!_isRunning || !mqtt || mqtt->getConnectionState() != eTCS_Connected) {
		_isRunning?debug_i("isRunning true"):debug_i("isRunning false");
		mqtt?debug_i("MQTT not null"):debug_i("MQTT null");
		mqtt->getConnectionState()==eTCS_Connected?debug_i("MQTT connected"):debug_i("MQTT not connected");
		reconnect();
        return false;
    }
	char fullTopic[TELEMETRY_TOPIC_MAX_SIZE];
    buildTopic(topic, fullTopic, sizeof(fullTopic));
	String payload;
	serializeJson(doc, payload);
    debug_i("Telemetry MQTT publishing %s to topic: %s", payload.c_str(), fullTopic);
	return mqtt->publish(fullTopic, payload);
}

bool TelemetryClient::publish(const String& topic, const JsonDocument& doc) {
    return publish(topic.c_str(), doc);
}

bool TelemetryClient::publish(const char* topic, const char* payload) {
    if (!_isRunning || !mqtt || mqtt->getConnectionState() != eTCS_Connected) {
        // Serial.println("Telemetry MQTT not connected");
        return false;
    }
    debug_i("Telemetry MQTT publishing %s to topic: %s", payload, topic);
    char fullTopic[TELEMETRY_TOPIC_MAX_SIZE];
    buildTopic(topic, fullTopic, sizeof(fullTopic));
    return mqtt->publish(fullTopic, payload);
}

bool TelemetryClient::publish(const String& topic, const String& payload) {
    return publish(topic.c_str(), payload.c_str());
}
bool TelemetryClient::stat(const JsonDocument& doc) {
	if(!_isRunning){
		return false; //stats disabled
	}
	return publish("monitor", doc);
}

bool TelemetryClient::log(const char* message) {
    if(!_isRunning){
		return false; //logging disabled
	}
    return publish("log", message);
}

bool TelemetryClient::log(const String& message) {
    return log(message.c_str());
}