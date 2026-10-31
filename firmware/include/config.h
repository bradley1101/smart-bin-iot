#pragma once

#ifndef BIN_ID
#define BIN_ID "bin-1"
#endif

// ---- pins (ESP32 DevKit V1)
#define PIN_FILL_TRIG   5    // HC-SR04 #1, under the lid, pointing down: fill level
#define PIN_FILL_ECHO   18   // through a 5V -> 3.3V divider (1k / 2k)
#define PIN_NEAR_TRIG   19   // HC-SR04 #2, on the front: someone approaching
#define PIN_NEAR_ECHO   21   // through a divider
#define PIN_LID_SERVO   13
#define PIN_LED_FULL    26   // red
#define PIN_LED_OK      27   // green

// ---- bin geometry
#define BIN_DEPTH_CM    40.0f   // sensor -> bottom of the empty bin
#define BIN_MIN_CM      4.0f    // distance when completely full

// ---- behaviour
#define FULL_PCT        85      // red LED + "full" status
#define NEAR_CM         40      // collector closer than this -> open lid
#define LID_OPEN_MS     6000    // lid stays open after the last detection
#define LID_CLOSED_DEG  0
#define LID_OPEN_DEG    100
#define REPORT_MS       15000   // periodic report to the server
#define REPORT_DELTA    5       // or immediately when the level changes by 5 points
