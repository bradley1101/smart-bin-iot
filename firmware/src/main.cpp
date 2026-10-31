// Smart bin node — ESP32
//  * HC-SR04 #1 under the lid measures the fill level (median of 5 readings)
//  * HC-SR04 #2 on the front detects the collector -> servo opens the lid
//  * reports {level, lid} to the Flask server, which raises the WhatsApp alert
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <algorithm>
#include "config.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Copy include/secrets.example.h to include/secrets.h"
#endif

static Servo lid;
static bool lidOpen = false;
static unsigned long lastNear = 0;
static int lastReportedLevel = -100;
static unsigned long lastReport = 0;

static float distanceCm(uint8_t trig, uint8_t echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  unsigned long us = pulseIn(echo, HIGH, 25000);
  return us == 0 ? -1 : us / 58.0f;
}

static int readFillPercent() {
  float v[5];
  int n = 0;
  for (int i = 0; i < 5; i++) {
    float d = distanceCm(PIN_FILL_TRIG, PIN_FILL_ECHO);
    if (d > 0) v[n++] = d;
    delay(30);
  }
  if (n == 0) return -1;                       // sensor error
  std::sort(v, v + n);
  float d = v[n / 2];
  float pct = 100.0f * (BIN_DEPTH_CM - d) / (BIN_DEPTH_CM - BIN_MIN_CM);
  return constrain((int)lroundf(pct), 0, 100);
}

static void setLid(bool open) {
  if (open == lidOpen) return;
  lidOpen = open;
  lid.write(open ? LID_OPEN_DEG : LID_CLOSED_DEG);
  Serial.println(open ? "Lid opened" : "Lid closed");
}

static void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("WiFi");
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++) {
    delay(300);
    Serial.print('.');
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " OK" : " failed");
}

static bool report(int level) {
  connectWifi();
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(String(SERVER_URL) + "/api/bins/" + BIN_ID + "/telemetry");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  String body = String("{\"level\":") + level + ",\"lid_open\":" + (lidOpen ? "true" : "false") +
                ",\"rssi\":" + WiFi.RSSI() + "}";
  int code = http.POST(body);
  http.end();
  Serial.printf("POST level=%d -> HTTP %d\n", level, code);
  return code == 200;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_FILL_TRIG, OUTPUT);
  pinMode(PIN_FILL_ECHO, INPUT);
  pinMode(PIN_NEAR_TRIG, OUTPUT);
  pinMode(PIN_NEAR_ECHO, INPUT);
  pinMode(PIN_LED_FULL, OUTPUT);
  pinMode(PIN_LED_OK, OUTPUT);
  lid.setPeriodHertz(50);
  lid.attach(PIN_LID_SERVO, 500, 2400);
  lid.write(LID_CLOSED_DEG);
  connectWifi();
  Serial.printf("Smart bin %s ready\n", BIN_ID);
}

void loop() {
  // 1. collector approaching -> open the lid, close it LID_OPEN_MS after the last detection
  float near = distanceCm(PIN_NEAR_TRIG, PIN_NEAR_ECHO);
  if (near > 0 && near < NEAR_CM) {
    lastNear = millis();
    setLid(true);
  } else if (lidOpen && millis() - lastNear > LID_OPEN_MS) {
    setLid(false);
  }

  // 2. fill level (measured lid closed, otherwise the sensor sees the sky)
  static int level = -1;
  static unsigned long lastMeasure = 0;
  if (!lidOpen && millis() - lastMeasure > 2000) {
    lastMeasure = millis();
    int l = readFillPercent();
    if (l >= 0) level = l;
  }
  digitalWrite(PIN_LED_FULL, level >= FULL_PCT);
  digitalWrite(PIN_LED_OK, level >= 0 && level < FULL_PCT);

  // 3. report periodically or on a significant change
  bool changed = level >= 0 && abs(level - lastReportedLevel) >= REPORT_DELTA;
  if (level >= 0 && (changed || millis() - lastReport > REPORT_MS)) {
    if (report(level)) lastReportedLevel = level;
    lastReport = millis();
  }
  delay(100);
}
