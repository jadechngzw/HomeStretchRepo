#include "board.h"
#include "sensors.h"
#include "config.h"
#include "ppg.h"
static uint8_t imu_ready;
static int set(uint8_t r,uint8_t v) {uint8_t got;return board_reg_write(0x6a,r,v)&&board_reg_read(0x6a,r,&got,1)&&got==v;}
static uint8_t crc(const uint8_t *d) {
    uint8_t c=255;for(unsigned i=0;i<2;i++){c^=d[i];for(unsigned j=0;j<8;j++)c=(c&128)?(c<<1)^0x31:c<<1;}return c;
}
int sensors_stop(void) {int a=set(0x10,0);int b=set(0x11,0);int c=ppg_stop();return a&&b&&c;}
int sensors_start(uint8_t mask) {
    if(!sensors_stop())return 0;
    imu_ready=((mask&1)?1:0)|((mask&8)?2:0);
    if(mask&9){uint8_t id;if(!board_reg_read(0x6a,0x0f,&id,1)||id!=0x6a||!set(0x12,0x44)||!set(0x10,(mask&1)?0x40:0)||!set(0x11,(mask&8)?0x40:0))goto fail;}
    if(mask&2){const uint8_t cmd[]={0xf3,0x2d};uint8_t b[3];if(!board_write(0x44,cmd,2)||!board_read(0x44,b,3)||crc(b)!=b[2])goto fail;}
    if((mask&4)&&!ppg_start(settings.leds,settings.ppg_hz))goto fail;
    return 1;
fail:(void)sensors_stop();return 0;
}
int sensors_imu(int16_t out[6]) {
    uint8_t status,b[12];
    if(!board_reg_read(0x6a,0x1e,&status,1)|| (status&imu_ready)!=imu_ready || !board_reg_read(0x6a,0x22,b,12))return 0;
    for(unsigned i=0;i<6;i++)out[i]=(int16_t)((uint16_t)b[i*2]|((uint16_t)b[i*2+1]<<8));return 1;
}
int sensors_temp_start(void) {const uint8_t cmd[]={0x24,0};return board_write(0x44,cmd,2);}
int sensors_temp_read(int16_t *t,int16_t *rh) {
    uint8_t b[6];if(!board_read(0x44,b,6)||crc(b)!=b[2]||crc(b+3)!=b[5])return 0;
    uint32_t rt=((uint32_t)b[0]<<8)|b[1],r=((uint32_t)b[3]<<8)|b[4];
    *t=(int16_t)(-4500+(int32_t)(17500*rt/65535));*rh=(int16_t)(10000*r/65535);return 1;
}
