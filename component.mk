# Sming component makefile

ifneq ("$(wildcard $(PROJECT_DIR)/credentials.txt)","")
    include $(PROJECT_DIR)/credentials.txt
endif

ifneq ("$(wildcard $(PROJECT_DIR)/Adafruit_MPU6050.patch)","")
    $(shell patch -d $(PROJECT_DIR)/Libraries/Adafruit_MPU6050 -p1 < $(PROJECT_DIR)/Adafruit_MPU6050.patch)
endif

APP_ID ?= "REMOTE_SENSORS"
MQTT_URL ?= "mqtt://lightinator.de:1883"
MQTT_USER ?= "default_user"
MQTT_PASS ?= "default_password"
WIFI_SSID ?= "default_ssid"
WIFI_PWD ?= "default_password"

COMPONENT_SEARCH_DIRS += $(PROJECT_DIR)/Libraries
LIBRARY_SEARCH_DIRS += $(PROJECT_DIR)/Libraries
ARDUINO_LIBRARIES := Arduino-Temperature-Control-Library OneWire Adafruit_BusIO Adafruit_Sensor
ARDUINO_LIBRARIES := Arduino-Temperature-Control-Library OneWire Adafruit_Sensor Adafruit_BusIO Adafruit_MPU6050 
#ARDUINO_LIBRARIES := Arduino-Temperature-Control-Library OneWire
COMPONENT_DEPENDS += LittleFS ArduinoJson6 Network OtaUpgradeMqtt 
COMPONENT_CPPFLAGS += -DCONFIG_ESP_CONSOLE_USB_CDC=1
#COMPONENT_CPPFLAGS += -I/opt/esp-idf-5.2/components/driver/rmt/include
DISABLE_NETWORK := 0
DISABLE_WIFI := 0
CONFIG_VARS += MQTT_URL MQTT_USER MQTT_PASS WIFI_SSID WIFI_PWD

APP_CFLAGS = -DMQTT_URL="\"$(MQTT_URL)\""                \
             -DMQTT_USER="\"$(MQTT_USER)\""              \
             -DMQTT_PASS="\"$(MQTT_PASS)\""              \
             -DWIFI_SSID="\"$(WIFI_SSID)\""              \
             -DWIFI_PWD="\"$(WIFI_PWD)\""                \
             -DAPP_ID="\"$(APP_ID)\""

