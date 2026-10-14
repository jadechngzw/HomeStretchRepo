#include <stdint.h>
int sensors_start(uint8_t mask);
int sensors_stop(void);
int sensors_imu(int16_t out[6]);
int sensors_temp_start(void);
int sensors_temp_read(int16_t *t,int16_t *rh);
