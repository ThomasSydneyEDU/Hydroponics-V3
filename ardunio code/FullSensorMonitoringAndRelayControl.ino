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

int lastMeasuredPh = -1;
int lastMeasuredEc = -1;

int lastMeasuredPhTop = -1;
int lastMeasuredEcTop = 100;
int lastMeasuredPhBottom = -2;
int lastMeasuredEcBottom = 200;

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
    // DS18B20 error fallback
    if (waterTemp1 == -127.0) waterTemp1 = -1;
    if (waterTemp2 == -127.0) waterTemp2 = -1;
    int phTop = lastMeasuredPhTop;
    int ecTop = lastMeasuredEcTop;
    int phBottom = lastMeasuredPhBottom;
    int ecBottom = lastMeasuredEcBottom;
    int temp = (int)dht.readTemperature(); // Convert float to int
    int humid = (int)dht.readHumidity();   // Convert float to int

    int floatTop = digitalRead(FLOAT_TOP_PIN);
    int floatBottom = digitalRead(FLOAT_BOTTOM_PIN);

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
    Serial.print(floatTop);
    Serial.print(",");
    Serial.print(floatBottom);
    Serial.print(",");
    Serial.print(temp);
    Serial.print(",");
    Serial.print(humid);
    Serial.print(",");
    Serial.print(waterTemp1);
    Serial.print(",");
    Serial.print(waterTemp2);
    Serial.print(",");
    Serial.print(phTop);
    Serial.print(",");
    Serial.print(ecTop);
    Serial.print(",");
    Serial.print(phBottom);
    Serial.print(",");
    Serial.println(ecBottom);
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
               command.startsWith("PT:") || command.startsWith("PB:")) {
        overrideDevice(command);
    //} else if (command.startsWith("ST:") || command.startsWith("SB:") || command.startsWith("DR:")) {
    //    overrideDevice(command);
    } else if (command == "GET_RELAYS") {
        sendRelayStatusOnly();
    } else if (command == "GET_SENSORS") {
        sendSensorStatusOnly();
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
    //} else if (command.startsWith("ST:")) {
    //    relayPin = RELAY_SENSOR_PUMP_TOP;
    //    deviceName = "Sensor Pump Top";
    //} else if (command.startsWith("SB:")) {
    //    relayPin = RELAY_SENSOR_PUMP_BOTTOM;
    //    deviceName = "Sensor Pump Bottom";
    //} else if (command.startsWith("DR:")) {
    //    relayPin = RELAY_DRAIN_ACTUATOR;
    //    deviceName = "Drain Actuator";
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
    if (overrideActive) return;

    // Lights on from 7:00 AM to 7:00 PM
    bool lightsOn = (hours >= 7 && hours < 19);
    digitalWrite(RELAY_LIGHTS_TOP, lightsOn ? HIGH : LOW);
    digitalWrite(RELAY_LIGHTS_BOTTOM, lightsOn ? HIGH : LOW);

    // Daytime pump schedule: 2 minutes on at 7, 9, 11, 13, 15, 17
    bool pumpOn = false;
    if (lightsOn && minutes < 2 &&
        (hours == 7 || hours == 9 || hours == 11 || hours == 13 || hours == 15 || hours == 17)) {
        pumpOn = true;
    }
    digitalWrite(RELAY_PUMP_TOP, pumpOn ? HIGH : LOW);
    digitalWrite(RELAY_PUMP_BOTTOM, pumpOn ? HIGH : LOW);

    /*
    // Morning bottom system measurement
    if (hours == 10 && minutes == 0 && seconds < 6) {
        digitalWrite(RELAY_SENSOR_PUMP_BOTTOM, HIGH);
    } else if (hours == 10 && minutes == 0 && seconds >= 6) {
        digitalWrite(RELAY_SENSOR_PUMP_BOTTOM, LOW);
    } else if (hours == 10 && minutes == 10) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, HIGH);
    } else if (hours == 10 && minutes == 15) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, LOW);
    }

    // Morning top system measurement
    if (hours == 10 && minutes == 20 && seconds < 6) {
        digitalWrite(RELAY_SENSOR_PUMP_TOP, HIGH);
    } else if (hours == 10 && minutes == 20 && seconds >= 6) {
        digitalWrite(RELAY_SENSOR_PUMP_TOP, LOW);
    } else if (hours == 10 && minutes == 30) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, HIGH);
    } else if (hours == 10 && minutes == 35) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, LOW);
    }

    // Afternoon bottom system measurement
    if (hours == 17 && minutes == 0 && seconds < 6) {
        digitalWrite(RELAY_SENSOR_PUMP_BOTTOM, HIGH);
    } else if (hours == 17 && minutes == 0 && seconds >= 6) {
        digitalWrite(RELAY_SENSOR_PUMP_BOTTOM, LOW);
    } else if (hours == 17 && minutes == 10) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, HIGH);
    } else if (hours == 17 && minutes == 15) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, LOW);
    }

    // Afternoon top system measurement
    if (hours == 17 && minutes == 20 && seconds < 6) {
        digitalWrite(RELAY_SENSOR_PUMP_TOP, HIGH);
    } else if (hours == 17 && minutes == 20 && seconds >= 6) {
        digitalWrite(RELAY_SENSOR_PUMP_TOP, LOW);
    } else if (hours == 17 && minutes == 30) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, HIGH);
    } else if (hours == 17 && minutes == 35) {
        digitalWrite(RELAY_DRAIN_ACTUATOR, LOW);
    }

    if ((hours == 10 && minutes == 5 && seconds == 0) || 
        (hours == 17 && minutes == 5 && seconds == 0)) {
        measureAndStoreAnalogSensors(false);  // bottom
    }
    if ((hours == 10 && minutes == 25 && seconds == 0) ||
        (hours == 17 && minutes == 25 && seconds == 0)) {
        measureAndStoreAnalogSensors(true);   // top
    }
    */
}

// TODO: revisit this function later
// Function to average analog sensors (PH and EC) for 1 minute and store results
/*
void measureAndStoreAnalogSensors(bool isTopSystem) {
    int floatTop = digitalRead(FLOAT_TOP_PIN);
    int floatBottom = digitalRead(FLOAT_BOTTOM_PIN);

    if ((isTopSystem && floatTop == 0) || (!isTopSystem && floatBottom == 0)) {
        Serial.println("Skipping EC/PH measurement due to low water level.");
        return;
    }

    const unsigned long duration = 60000;
    unsigned long startTime = millis();
    int phSum = 0;
    int ecSum = 0;
    int count = 0;

    while (millis() - startTime < duration) {
        phSum += analogRead(PH_PIN);
        ecSum += analogRead(EC_PIN);
        count++;
        delay(200);
    }

    if (isTopSystem) {
        lastMeasuredPhTop = phSum / count;
        lastMeasuredEcTop = ecSum / count;
    } else {
        lastMeasuredPhBottom = phSum / count;
        lastMeasuredEcBottom = ecSum / count;
    }

    Serial.print("AVG_PH:");
    Serial.print(isTopSystem ? lastMeasuredPhTop : lastMeasuredPhBottom);
    Serial.print(" AVG_EC:");
    Serial.println(isTopSystem ? lastMeasuredEcTop : lastMeasuredEcBottom);
}
*/

void sendRelayStatusOnly() {
    Serial.print("RELAYS:");
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
    Serial.println(digitalRead(RELAY_DRAIN_ACTUATOR));
}

void sendSensorStatusOnly() {
    waterSensors.requestTemperatures();
    float waterTemp1 = waterSensors.getTempC(tempSensor1);
    float waterTemp2 = waterSensors.getTempC(tempSensor2);
    if (waterTemp1 == -127.0) waterTemp1 = -1;
    if (waterTemp2 == -127.0) waterTemp2 = -1;

    int temp = (int)dht.readTemperature();
    int humid = (int)dht.readHumidity();
    if (isnan(temp) || isnan(humid)) {
        temp = -1;
        humid = -1;
    }

    int floatTop = digitalRead(FLOAT_TOP_PIN);
    int floatBottom = digitalRead(FLOAT_BOTTOM_PIN);

    Serial.print("SENSORS:");
    Serial.print(temp);
    Serial.print(",");
    Serial.print(humid);
    Serial.print(",");
    Serial.print(waterTemp1);
    Serial.print(",");
    Serial.print(waterTemp2);
    Serial.print(",");
    Serial.print(floatTop);
    Serial.print(",");
    Serial.println(floatBottom);
}