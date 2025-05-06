// Digital Pins
#define DHTPIN 3
#define DS18B20_PIN 4
#define FLOAT_TOP_PIN 5
#define FLOAT_BOTTOM_PIN 6
#define RELAY_SENSOR_PUMP_TOP 7
#define RELAY_SENSOR_PUMP_BOTTOM 8
#define RELAY_DRAIN_ACTUATOR 9
#define RELAY_LIGHTS_TOP 10
#define RELAY_LIGHTS_BOTTOM 11
#define RELAY_PUMP_TOP 12
#define RELAY_PUMP_BOTTOM 13

// Analog Pins
#define PH_PIN A0
#define EC_PIN A1

// Include DHT Sensor Library
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>

#include <OneWire.h>
#include <DallasTemperature.h>

// Define DHT Sensor Type
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

OneWire oneWire(DS18B20_PIN);
DallasTemperature waterSensors(&oneWire);
DeviceAddress tempSensor1, tempSensor2;

// Time tracking variables
int hours = 0, minutes = 0, seconds = 0;
unsigned long lastMillis = 0;
unsigned long lastStateUpdate = 0;
unsigned long lastSensorUpdate = 0;

// Manual override tracking
bool overrideActive = false;
unsigned long overrideEndTime = 0;  // Overrides expire after 10 minutes

void setup() {
    // Set relay pins as outputs
    pinMode(RELAY_LIGHTS_TOP, OUTPUT);
    pinMode(RELAY_LIGHTS_BOTTOM, OUTPUT);
    pinMode(RELAY_PUMP_TOP, OUTPUT);
    pinMode(RELAY_PUMP_BOTTOM, OUTPUT);
    pinMode(RELAY_SENSOR_PUMP_TOP, OUTPUT);
    pinMode(RELAY_SENSOR_PUMP_BOTTOM, OUTPUT);
    pinMode(RELAY_DRAIN_ACTUATOR, OUTPUT);

    // Initialize serial communication
    Serial.begin(9600);
    delay(2000);  // Allow serial connection to stabilize

    // Initialize DHT Sensor
    dht.begin();

    waterSensors.begin();
    if (!waterSensors.getAddress(tempSensor1, 0)) {
      Serial.println("Error: Water Temp Sensor 1 not found.");
    }
    if (!waterSensors.getAddress(tempSensor2, 1)) {
      Serial.println("Error: Water Temp Sensor 2 not found.");
    }

    Serial.println("Arduino is ready. Default time: 00:00. Running schedule.");
}

void loop() {
    unsigned long currentMillis = millis();

    // Increment time every second
    if (currentMillis - lastMillis >= 1000) {
        lastMillis = currentMillis;
        incrementTime();
        if (!overrideActive) {
            runSchedule();
        }
    }

    // Send relay state every 10 seconds
    if (currentMillis - lastStateUpdate >= 10000) {
        lastStateUpdate = currentMillis;
        sendRelayState();
    }

    // If override has expired, return to schedule
    if (overrideActive && millis() >= overrideEndTime) {
        overrideActive = false;
        Serial.println("Override expired. Resuming schedule.");
        runSchedule();
    }

    // Listen for Pi commands
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        handleCommand(command);
        sendRelayState();  // Send updated state immediately after a change
    }
}

// Function to send relay states and sensor data to the Pi
void sendRelayState() {
    // Read sensor values
    waterSensors.requestTemperatures();
    float waterTemp1 = waterSensors.getTempC(tempSensor1);
    float waterTemp2 = waterSensors.getTempC(tempSensor2);
    int ph = analogRead(PH_PIN);
    int ec = analogRead(EC_PIN);
    int temp = (int)dht.readTemperature(); // Convert float to int
    int humid = (int)dht.readHumidity();   // Convert float to int

    // If sensor readings fail, send default values (-1)
    if (isnan(temp) || isnan(humid)) {
        temp = -1;
        humid = -1;
    }

    Serial.print("STATE:");
    Serial.print(digitalRead(RELAY_LIGHTS_TOP));
    Serial.print(",");
    Serial.print(digitalRead(RELAY_LIGHTS_BOTTOM));
    Serial.print(",");
    Serial.print(digitalRead(RELAY_PUMP_TOP));
    Serial.print(",");
    Serial.print(digitalRead(RELAY_PUMP_BOTTOM));
    Serial.print(",");
    Serial.print(digitalRead(RELAY_SENSOR_PUMP_TOP));
    Serial.print(",");
    Serial.print(digitalRead(RELAY_SENSOR_PUMP_BOTTOM));
    Serial.print(",");
    Serial.print(digitalRead(RELAY_DRAIN_ACTUATOR));
    Serial.print(",");
    Serial.print(temp);
    Serial.print(",");
    Serial.print(humid);
    Serial.print(",");
    Serial.print(waterTemp1);
    Serial.print(",");
    Serial.print(waterTemp2);
    Serial.print(",");
    Serial.print(ph);
    Serial.print(",");
    Serial.println(ec);
}

// Function to read and send temperature & humidity
void sendSensorData() {
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();  // Celsius

    if (isnan(humidity) || isnan(temperature)) {
        Serial.println("TEMP:ERROR | HUM:ERROR");
        return;
    }

    Serial.print("TEMP:");
    Serial.print(temperature);
    Serial.print(" | HUM:");
    Serial.println(humidity);
}

// Function to process commands from the Raspberry Pi
void handleCommand(String command) {
    if (command == "PING") {
        Serial.println("PING_OK");
    } else if (command.startsWith("SET_TIME:")) {
        setTimeFromPi(command.substring(9));
        Serial.println("SET_TIME OK");
        sendRelayState();
    } else if (command == "RESET_SCHEDULE") {  
        Serial.println("Schedule reset. Resuming automatic control.");
        overrideActive = false;  
        runSchedule();  
        sendRelayState();  
    } else if (command.startsWith("LT:") || command.startsWith("LB:") || 
               command.startsWith("PT:") || command.startsWith("PB:") ||
               command.startsWith("ST:") || command.startsWith("SB:") || command.startsWith("DR:")) {
        overrideDevice(command);
    } else {
        Serial.println("Unknown command: " + command);
    }
}

// Function to override a specific device
void overrideDevice(String command) {
    int relayPin;
    String deviceName;

    if (command.startsWith("LT:")) {
        relayPin = RELAY_LIGHTS_TOP;
        deviceName = "Lights Top";
    } else if (command.startsWith("LB:")) {
        relayPin = RELAY_LIGHTS_BOTTOM;
        deviceName = "Lights Bottom";
    } else if (command.startsWith("PT:")) {
        relayPin = RELAY_PUMP_TOP;
        deviceName = "Pump Top";
    } else if (command.startsWith("PB:")) {
        relayPin = RELAY_PUMP_BOTTOM;
        deviceName = "Pump Bottom";
    } else if (command.startsWith("ST:")) {
        relayPin = RELAY_SENSOR_PUMP_TOP;
        deviceName = "Sensor Pump Top";
    } else if (command.startsWith("SB:")) {
        relayPin = RELAY_SENSOR_PUMP_BOTTOM;
        deviceName = "Sensor Pump Bottom";
    } else if (command.startsWith("DR:")) {
        relayPin = RELAY_DRAIN_ACTUATOR;
        deviceName = "Drain Actuator";
    } else {
        Serial.println("Unknown command: " + command);
        return;
    }

    String state = command.substring(3);
    if (state == "ON") {
        digitalWrite(relayPin, HIGH);
        overrideActive = true;
        overrideEndTime = millis() + 600000; // 10-minute override
        Serial.println(deviceName + " overridden to ON.");
    } else if (state == "OFF") {
        digitalWrite(relayPin, LOW);
        overrideActive = true;
        overrideEndTime = millis() + 600000;
        Serial.println(deviceName + " overridden to OFF.");
    } else {
        Serial.println("Invalid state for " + deviceName + ": " + state);
    }

    sendRelayState();
}

// Function to set time from the Raspberry Pi
void setTimeFromPi(String timeString) {
    int firstColon = timeString.indexOf(':');
    int secondColon = timeString.lastIndexOf(':');

    if (firstColon > 0 && secondColon > firstColon) {
        hours = timeString.substring(0, firstColon).toInt();
        minutes = timeString.substring(firstColon + 1, secondColon).toInt();
        seconds = timeString.substring(secondColon + 1).toInt();
        Serial.print("Time set to: ");
        Serial.print(hours);
        Serial.print(":");
        Serial.print(minutes);
        Serial.print(":");
        Serial.println(seconds);

        // Resume schedule after time update
        overrideActive = false;
        runSchedule();
    } else {
        Serial.println("Invalid time format!");
    }
}

// Function to increment time every second
void incrementTime() {
    seconds++;
    if (seconds >= 60) {
        seconds = 0;
        minutes++;
        if (minutes >= 60) {
            minutes = 0;
            hours++;
            if (hours >= 24) {
                hours = 0;
            }
        }
    }
}

// Function to run the schedule
void runSchedule() {
    if (overrideActive) return; // Skip schedule if overridden

    // **Lights Schedule (9 AM - 9 PM)**
    bool lightsState = (hours >= 9 && hours < 21);
    digitalWrite(RELAY_LIGHTS_TOP, lightsState ? HIGH : LOW);
    digitalWrite(RELAY_LIGHTS_BOTTOM, lightsState ? HIGH : LOW);

    // **Pumps Schedule (15 minutes every 4 hours)**
    bool pumpsState = (minutes < 15) && (hours % 4 == 0);
    digitalWrite(RELAY_PUMP_TOP, pumpsState ? HIGH : LOW);
    digitalWrite(RELAY_PUMP_BOTTOM, pumpsState ? HIGH : LOW);
}