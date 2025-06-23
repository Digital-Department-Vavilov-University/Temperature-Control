#include <functions.h>
#define SHOW_DEBUG_STRINGS
//коды из апи
const int goodConditions[] = {1000, 1003, 1006, 1009, 1030, 1063};

//Если погода без осадков, то вернём true. Коды берутся из api
bool checkCondition(int conditionCode)
{
  bool t = false;

  for (auto i : goodConditions)
  {
    if (i == conditionCode)
    {
      return true;
    }
  }
  return false;
}


//если хотим открыть окно, то возвращаем true
bool openCloseDetermine(float desiredTemperature, bool conditionState, float outsideTemperature, float insideTemperature)
{
  //откусим дробную часть, чтобы не открывать закрывать окно постоянно
  outsideTemperature = (int)outsideTemperature;
  insideTemperature = (int)insideTemperature;

  //если плохая погода, то точно закрываем
  if (!conditionState)
  {
    #ifdef SHOW_DEBUG_STRINGS
    Serial.println("BAD WEATHER");
    #endif
    return false;
  }

  //если меньше нуля, то точно закрываем
  if (outsideTemperature < 0)
  {
    #ifdef SHOW_DEBUG_STRINGS
    Serial.println("LESS THAN ZERO");
    #endif
    return false;
  }

  //если внутри теплее, чем должно быть
  if (desiredTemperature < insideTemperature)
  {
    //и на улице прохладнее
    if (outsideTemperature < insideTemperature)
    {
      #ifdef SHOW_DEBUG_STRINGS
      Serial.println("COLDER AT STREET NEED TO OPEN");
      #endif
      //то открываем окно
      return true;
    }
    else
    {
      #ifdef SHOW_DEBUG_STRINGS
      Serial.println("NO POINT TO OPEN BUT NEED TO BE COLDER");
      #endif
      //иначе смысла открывать нет
      return false;
    }
  }

  //если температура внутри недостаточна
  if (desiredTemperature > insideTemperature)
  {
    //если вдруг на улице теплее
    if (outsideTemperature > insideTemperature)
    {
      #ifdef SHOW_DEBUG_STRINGS
      Serial.println("WARMER AT STREET NEED TO OPEN");
      #endif
      return true;
    }
    else
    {
      #ifdef SHOW_DEBUG_STRINGS
      Serial.println("NO POINT TO OPEN BUT ITS COLD");
      #endif
      return false;
    }
  }

  //почему-то свалились сюда
  return false;
}