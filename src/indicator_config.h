/* RGB colours and brightness for status lights, independent of RGB_TOG. */
#define INDICATOR_COLOR 0x00FFFF
#define BATTERY_COLOR_NORMAL 0x00FF00
#define BATTERY_COLOR_LOW 0xFFFF00
#define BATTERY_COLOR_CRITICAL 0xFF0000
#define INDICATOR_BRIGHTNESS_PERCENT 10
#define BATTERY_DISPLAY_MS 10000

/* Measured independently on both halves, outside to inside. */
#define BATTERY_LED_INDEXES {31, 25, 19, 13, 7}
#define MOD_LED 7
#define CONTROL_LED 13
#define DVORAK_LED 19
#define PASTE_LED 1 /* Left half only. Thumb LED 39 deliberately unused. */
