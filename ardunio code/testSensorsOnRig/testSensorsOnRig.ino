#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>

// ---------- Pins ----------
#define ONE_WIRE_BUS 4         // DS18B20 (Water Temp)
#define FLOAT_TOP 5            // Float sensor top
#define FLOAT_BOTTOM 6         // Float sensor bottom
#define DHTPIN 3               // Air Temp & Humidity
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ---------- Relays ----------
const int relayPins[] = {7, 8, 9, 10, 11, 12, 13};
const char* relayLabels[] = {
  "Top Sensor Pump",
  "Bottom Sensor Pump",
  "Drain Actuator",
  "Top Light",
  "Bottom Light",
  "Top Pump",
  "Bottom Pump"
};
const int numRelays = sizeof(relayPins) / sizeof(relayPins[0]);

// ---------- DS18B20 ----------
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// ---------- Timing ----------
int currentRelay = 0;
unsigned long lastSwitchTime = 0;
const unsigned long interval = 3000;  // 3 seconds

void setup() {
  Serial.begin(9600);
  delay(1000);
  Serial.println("=== Dynamic Hydroponic System Monitor ===");

  // Relays
  for (int i = 0; i < numRelays; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], HIGH); // DE-energized = OFF
  }

  // Inputs
  pinMode(FLOAT_TOP, INPUT_PULLUP);
  pinMode(FLOAT_BOTTOM, INPUT_PULLUP);

  // Sensors
  sensors.begin();
  dht.begin();
}

void loop() {
  unsigned long currentTime = millis();

  if (currentTime - lastSwitchTime >= interval) {
    // Turn all relays OFF (HIGH = OFF for active-low relay)
    for (int i = 0; i < numRelays; i++) {
      digitalWrite(relayPins[i], HIGH);
    }

    // Turn ON current relay (LOW = ON for active-low relay)
    digitalWrite(relayPins[currentRelay], LOW);

    Serial.print("Active Relay (D");
    Serial.print(relayPins[currentRelay]);
    Serial.print("): ");
    Serial.println(relayLabels[currentRelay]);

    // Water temp sensors
    sensors.requestTemperatures();
    int count = sensors.getDeviceCount();
    for (int i = 0; i < count; i++) {
      float tempC = sensors.getTempCByIndex(i);
      Serial.print("  Water Temp Sensor ");
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(tempC);
      Serial.println(" °C");
    }

    // Air temp and humidity
    float airTemp = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(airTemp) || isnan(humidity)) {
      Serial.println("  Air Temp/Humidity: ERROR");
    } else {
      Serial.print("  Air Temp (°C): ");
      Serial.print(airTemp);
      Serial.print(" | Humidity (%): ");
      Serial.println(humidity);
    }

    // Float sensors
    Serial.print("  Top Float Sensor (D5): ");
    Serial.println(digitalRead(FLOAT_TOP) == LOW ? "UP (FLOATING)" : "DOWN (NOT FLOATING)");

    Serial.print("  Bottom Float Sensor (D6): ");
    Serial.println(digitalRead(FLOAT_BOTTOM) == LOW ? "UP (FLOATING)" : "DOWN (NOT FLOATING)");

    Serial.println("----");

    // Cycle relay
    currentRelay = (currentRelay + 1) % numRelays;
    lastSwitchTime = currentTime;
  }
}