#ifndef FUNCTIONS_H_
#define FUNCTIONS_H_
#include <Arduino.h>


bool checkCondition(int contidionCode);

bool openCloseDetermine(float desiredTemperature, bool conditionState, float outsideTemperature, float insideTemperature);
#endif