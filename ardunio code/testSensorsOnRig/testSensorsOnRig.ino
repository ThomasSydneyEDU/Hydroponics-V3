#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>

// ----------- Pin Definitions -----------

// Digital sensors
#define DHTPIN 3
#define DHTTYPE DHT11
#define WATER_TEMP_PIN 4
#define FLOAT_TOP_PIN 5
#define FLOAT_BOTTOM_PIN 6

// Relays
#define RELAY_SENSOR_PUMP_TOP 7
#define RELAY_SENSOR_PUMP_BOTTOM 8
#define RELAY_DRAIN_ACTUATOR 9
#define RELAY_LIGHT_TOP 10
#define RELAY_LIGHT_BOTTOM 11
#define RELAY_PUMP_TOP 12
#define RELAY_PUMP_BOTTOM 13

// Analog sensors
#define PH_PIN A0
#define EC_PIN A1

DHT dht(DHTPIN, DHTTYPE);

// Array of relay pins
const int relayPins[] = {
  RELAY_SENSOR_PUMP_TOP,
  RELAY_SENSOR_PUMP_BOTTOM,
  RELAY_DRAIN_ACTUATOR,
  RELAY_LIGHT_TOP,
  RELAY_LIGHT_BOTTOM,
  RELAY_PUMP_TOP,
  RELAY_PUMP_BOTTOM
};

const char* relayNames[] = {
  "Sensor Pump Top",
  "Sensor Pump Bottom",
  "Drain Actuator",
  "Light Top",
  "Light Bottom",
  "Pump Top",
  "Pump Bottom"
};

void setup() {
  Serial.begin(9600);
  delay(2000);
  Serial.println("Hydroponics System Test Starting...");

  // Initialize DHT
  dht.begin();

  // Set up sensor pins
  pinMode(FLOAT_TOP_PIN, INPUT);
  pinMode(FLOAT_BOTTOM_PIN, INPUT);
  pinMode(WATER_TEMP_PIN, INPUT); // placeholder

  // Set up relay pins and turn all OFF
  for (int i = 0; i < sizeof(relayPins) / sizeof(int); i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW);
  }

  // -------- Relay Test: Cycle one at a time --------
  Serial.println("Cycling relays to test...");
  for (int i = 0; i < sizeof(relayPins) / sizeof(int); i++) {
    Serial.print("Turning ON: ");
    Serial.println(relayNames[i]);
    digitalWrite(relayPins[i], HIGH);
    delay(1000);
    digitalWrite(relayPins[i], LOW);
  }
  Serial.println("Relay test complete.");
}

void loop() {
  float airTemp = dht.readTemperature();
  float humidity = dht.readHumidity();
  int floatTop = digitalRead(FLOAT_TOP_PIN);
  int floatBottom = digitalRead(FLOAT_BOTTOM_PIN);
  int phValue = analogRead(PH_PIN);
  int ecValue = analogRead(EC_PIN);

  Serial.println("------------- SENSOR READINGS -------------");

  if (isnan(airTemp) || isnan(humidity)) {
    Serial.println("Air Temp/Humidity: ERROR");
  } else {
    Serial.print("Air Temp (°C): ");
    Serial.print(airTemp);
    Serial.print(" | Humidity (%): ");
    Serial.println(humidity);
  }

  Serial.print("Float Sensor - Top: ");
  Serial.print(floatTop ? "HIGH" : "LOW");
  Serial.print(" | Bottom: ");
  Serial.println(floatBottom ? "HIGH" : "LOW");

  // Serial.print("pH sensor (A0 raw): ");
  // Serial.print(phValue);
  // Serial.print(" | EC sensor (A1 raw): ");
  // Serial.println(ecValue);

  Serial.println("All relays OFF. Looping again in 5 seconds...");
  delay(5000);
}