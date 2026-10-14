#ifndef VW_PPG_H
#define VW_PPG_H
#include <stdint.h>
int ppg_start(uint8_t leds,unsigned hz);
int ppg_stop(void);
int ppg_pending(unsigned *n);
int ppg_read(uint32_t values[4]);
#endif
