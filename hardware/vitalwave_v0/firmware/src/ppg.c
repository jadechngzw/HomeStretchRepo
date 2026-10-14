/* MAX86916: FIFO slots IR, red, green, blue; 2 mA per selected LED. */
#include "board.h"
#include "ppg.h"
static uint8_t active,channels[4],count;
static int checked(uint8_t reg,uint8_t value){uint8_t v;return board_reg_write(0x57,reg,value)&&board_reg_read(0x57,reg,&v,1)&&v==value;}
int ppg_stop(void){
    if(!active)return board_ppg_off();
    int ok=checked(9,0x80);
    for(uint8_t r=12;r<=15;r++){int a=checked(r,0);ok=a&&ok;}
    if(ok)active=0;return ok;
}
int ppg_start(uint8_t leds,unsigned hz){
    uint8_t id,mode;count=0;
    if(!leds||leds>15||(hz!=50&&hz!=100))return 0;
    if(!board_reg_read(0x57,0xff,&id,1)||id!=0x2b)return 0;
    active=1;
    if(!board_reg_write(0x57,9,0x40))goto fail;
    unsigned n;for(n=0;n<100;n++){board_delay_us(1000);if(!board_reg_read(0x57,9,&mode,1))goto fail;if(!(mode&0x40))break;}
    if(n==100||!checked(9,0)||!checked(2,0)||!checked(0x11,0)||!checked(0x12,0))goto fail;
    uint8_t slots[4]={0};
    for(unsigned i=0;i<4;i++){
        if(leds&(1u<<i)){channels[count]=i;slots[count++]=i+1;}
        if(!checked(12+i,(leds&(1u<<i))?10:0))goto fail;
    }
    if(!checked(10,hz==50?0x22:0x26)||!checked(8,0)||!checked(0x13,slots[0]|(slots[1]<<4))||!checked(0x14,slots[2]|(slots[3]<<4)))goto fail;
    if(!checked(4,0)||!checked(5,0)||!checked(6,0)||!board_reg_read(0x57,0,&mode,1)||!checked(9,3))goto fail;
    return 1;
fail:(void)ppg_stop();return 0;
}
int ppg_pending(unsigned *n){
    uint8_t p[3],status;
    if(!board_reg_read(0x57,0,&status,1)||(status&0x21)||!board_reg_read(0x57,4,p,3)||(p[1]&31))return 0;
    *n=(p[0]-p[2])&31;return 1;
}
int ppg_read(uint32_t values[4]){
    uint8_t raw[12];if(!board_reg_read(0x57,7,raw,3*count))return 0;
    for(unsigned i=0;i<count;i++)values[channels[i]]=(((uint32_t)raw[3*i]<<16)|((uint32_t)raw[3*i+1]<<8)|raw[3*i+2])&0x7ffff;
    return 1;
}
