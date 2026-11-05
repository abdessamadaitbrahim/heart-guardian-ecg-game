// Heart Guardian - ESP32 ECG streamer
//
// Samples the ECG sensor at 100 Hz and streams it over WiFi (TCP) to the
// Python pipeline as text lines:
//   ECG:<0-4095>   one raw 12-bit ADC sample
//   DECONNECTE     electrodes are not attached (leads-off detection)
//
// Wiring assumes an AD8232-type ECG module. Adjust the pins below to match
// your wiring. The output pin must be an ADC1 pin (32-39): ADC2 does not work
// while WiFi is active.

#include <WiFi.h>
#include "secrets.h"

const int ECG_PIN      = 34;   // sensor analog output
const int LO_PLUS_PIN  = 32;   // leads-off detect +
const int LO_MINUS_PIN = 33;   // leads-off detect -

const int SAMPLE_RATE_HZ = 100;
const unsigned long SAMPLE_INTERVAL_US = 1000000UL / SAMPLE_RATE_HZ;
const unsigned long RECONNECT_INTERVAL_MS = 2000;
const unsigned long LEADS_OFF_REPORT_MS = 1000;

WiFiClient client;
unsigned long nextSampleUs = 0;
unsigned long lastReconnectMs = 0;
unsigned long lastLeadsOffMs = 0;

void connectWifi() {
  Serial.printf("Connecting to WiFi %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConnected, IP: %s\n", WiFi.localIP().toString().c_str());
}

void connectServer() {
  if (client.connect(SERVER_IP, SERVER_PORT)) {
    client.setNoDelay(true);
    Serial.println("Connected to pipeline");
  } else {
    Serial.println("Pipeline not reachable, retrying");
  }
}

bool leadsOff() {
  return digitalRead(LO_PLUS_PIN) == HIGH || digitalRead(LO_MINUS_PIN) == HIGH;
}

void setup() {
  Serial.begin(115200);
  pinMode(ECG_PIN, INPUT);
  pinMode(LO_PLUS_PIN, INPUT);
  pinMode(LO_MINUS_PIN, INPUT);
  analogReadResolution(12);
  connectWifi();
  connectServer();
  nextSampleUs = micros();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  if (!client.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectMs >= RECONNECT_INTERVAL_MS) {
      lastReconnectMs = now;
      connectServer();
    }
    return;
  }

  if ((long)(micros() - nextSampleUs) < 0) {
    return;
  }
  nextSampleUs += SAMPLE_INTERVAL_US;

  if (leadsOff()) {
    unsigned long now = millis();
    if (now - lastLeadsOffMs >= LEADS_OFF_REPORT_MS) {
      lastLeadsOffMs = now;
      client.print("DECONNECTE\n");
    }
    return;
  }

  client.printf("ECG:%d\n", analogRead(ECG_PIN));
}
