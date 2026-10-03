#ifndef VW_CONFIG_H
#define VW_CONFIG_H
#include <stdint.h>
/* GUI stream rates; IMU internal ODR stays 104 Hz. */
typedef struct {uint16_t imu_hz,temp_ms,ppg_hz;uint8_t leds;} Settings;
extern Settings settings;
int settings_apply(uint32_t packed);
#endif
