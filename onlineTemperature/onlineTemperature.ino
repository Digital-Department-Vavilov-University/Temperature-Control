#include <WiFi.h>
#include <WiFiMulti.h>

#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <functions.h>
#include <AHT20.h>
#include <NetworkClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>

const char SSID[] = "SSID";
const char pwd[] = "PASSWORD";

const int OPEN_ANGLE = 90;
const int CLOSE_ANGLE = 0;

const int UPDATE_PERIOD = 5000;
const float DESIRED_TEMPERATURE = 20;
const char* SERVER_URL = "http://192.168.1.61:5000/data";
WiFiMulti wifiMulti;
Servo servo;
AHT20 aht20;

int conditionCode;
float onlineTemperature;


void setup() {
  // put your setup code here, to run once:
  wifiMulti.addAP("SSID", "PASSWORD");
  Serial.begin(115200);

  servo.attach(32);

  Wire.begin();
  if (aht20.begin() == false)
  {
    Serial.println("AHT20 not detected. Please check wiring. Freezing.");
    while(true);
  }

  //check servo
  for (int i = 0; i <= 90; i++)
  {
    servo.write(i);
    delay(15);
  }

}

void sendToServer(float offlineTemp, float onlineTemp, bool isOpen, int conditionCode) {
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  
  // Формирование JSON
  JsonDocument doc;
  doc["offlineTemperature"] = offlineTemp;
  doc["onlineTemperature"] = onlineTemp;
  doc["isOpen"] = isOpen;
  doc["conditionCode"] = conditionCode;
  
  String json;
  serializeJson(doc, json);
  
  Serial.print("Sending data: ");
  Serial.println(json);
  
  int httpCode = http.POST(json);
  
  if (httpCode == HTTP_CODE_OK) {
    Serial.println("Data sent successfully");
  } else {
    Serial.printf("HTTP error: %d\n", httpCode);
  }
  
  http.end();
}

void loop() {
  // put your main code here, to run repeatedly:
  if (!(wifiMulti.run() == WL_CONNECTED))
  {
    Serial.println("No connect");
  }
  else
  {
    HTTPClient http;
    //http.begin("http://api.weatherapi.com/v1/current.json");

    http.begin("API KEY"); //Саратов захардкожен

    int httpCode = http.GET();
    if (httpCode > 0) {
      // HTTP header has been send and Server response header has been handled
      Serial.printf("[HTTP] GET... code: %d\n", httpCode);

      // file found at server
      if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        Serial.println(payload);

        JsonDocument doc;

        deserializeJson(doc, payload);

        onlineTemperature = doc["current"]["temp_c"].as<float>();
        conditionCode = doc["current"]["condition"]["code"].as<int>();
        Serial.println(onlineTemperature);
        Serial.println(checkCondition(conditionCode));
      }
    } else {
      Serial.printf("[HTTP] GET... failed, error: %s\n", http.errorToString(httpCode).c_str());
    }

    http.end();
    
    //aht20 block
    float offlineTemperature = aht20.getTemperature();
    Serial.print("AHT20 TEMP: ");
    Serial.println(offlineTemperature);

    //open/close block
    //conditionCode = 1000;
    bool openFlag = openCloseDetermine(DESIRED_TEMPERATURE, checkCondition(conditionCode), onlineTemperature, offlineTemperature);
    Serial.print("Open/close flag state: ");
    Serial.println(openFlag);
    if (openFlag)
    {
      servo.write(OPEN_ANGLE);
    }
    else
    {
      servo.write(CLOSE_ANGLE);
    }

    delay(UPDATE_PERIOD);
    sendToServer(offlineTemperature, onlineTemperature, openFlag, conditionCode);
  }
}
