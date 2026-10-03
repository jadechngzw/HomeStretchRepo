/* VitalWave v3: three-colour PPG capture with charger monitoring.
 * SDA=P0.19, SCL=P0.20, UART TX=P0.23. 115200 baud, 8N1.
 * Software I2C uses open-drain GPIO and external schematic pullups.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nrf.h"
#include "board.h"
#define SDA 19u
#define SCL 20u
static int bus_error;
uint32_t board_ms(void) { static uint32_t last,ms,remainder; NRF_TIMER2->TASKS_CAPTURE[0]=1; uint32_t now=NRF_TIMER2->CC[0],delta=now-last;last=now;ms+=delta/1000;remainder+=delta%1000;ms+=remainder/1000;remainder%=1000;return ms; }
static uint32_t now_us(void) { NRF_TIMER2->TASKS_CAPTURE[1]=1;return NRF_TIMER2->CC[1]; }
void board_delay_us(uint32_t n) {uint32_t t=now_us();while((uint32_t)(now_us()-t)<n){}}
#define us board_delay_us
static void release(uint32_t p) { NRF_P0->DIRCLR=1u<<p; }
static void low(uint32_t p) { NRF_P0->OUTCLR=1u<<p; NRF_P0->DIRSET=1u<<p; }
static int level(uint32_t p) { return (NRF_P0->IN>>p)&1u; }
static int clock_high(void) {
    release(SCL);
    for (unsigned i=0;i<1000;i++) {
        if(level(SCL)) { us(5); return 1; }
        us(10);
    }
    bus_error=1; return 0;
}
static int start(void) {
    release(SDA); us(5);
    if(!clock_high()) return 0;
    if(!level(SDA)) { bus_error=1; return 0; }
    low(SDA);us(5);low(SCL);us(5);return 1;
}
static void stop(void) {
    low(SCL);low(SDA);us(5);
    (void)clock_high();release(SDA);us(5);
}
static int put(uint8_t v) {
    for(unsigned i=0;i<8;i++) {
        if(v&0x80) release(SDA); else low(SDA);
        us(5);if(!clock_high()) return 0;low(SCL);us(5);v<<=1;
    }
    release(SDA);us(5);if(!clock_high()) return 0;
    int ack=!level(SDA);low(SCL);us(5);return ack;
}
static int get(uint8_t *v, int ack) {
    *v=0;release(SDA);
    for(unsigned i=0;i<8;i++) {
        us(5);if(!clock_high()) return 0;
        *v=(uint8_t)((*v<<1)|level(SDA));low(SCL);us(5);
    }
    if(ack) low(SDA);else release(SDA);
    us(5);if(!clock_high()) return 0;
    low(SCL);us(5);release(SDA);return 1;
}
static int read_command(uint8_t addr,const uint8_t *cmd,unsigned n,uint8_t *out,unsigned len) {
    bus_error=0;
    int ok=start() && put((uint8_t)(addr<<1));
    for(unsigned i=0;ok && i<n;i++) ok=put(cmd[i]);
    if(ok) ok=start() && put((uint8_t)((addr<<1)|1));
    for(unsigned i=0;ok && i<len;i++) ok=get(out+i,i+1<len);
    stop();return ok && !bus_error;
}

void board_init(void) {
    NRF_TIMER2->TASKS_STOP=1;NRF_TIMER2->MODE=0;NRF_TIMER2->BITMODE=3;
    NRF_TIMER2->PRESCALER=4;NRF_TIMER2->TASKS_CLEAR=1;NRF_TIMER2->TASKS_START=1;
    NRF_P0->PIN_CNF[SDA]=0;NRF_P0->PIN_CNF[SCL]=0;
    NRF_P0->PIN_CNF[12]=3u<<2;
    NRF_P0->PIN_CNF[13]=3u<<2;NRF_P0->PIN_CNF[3]=3u<<2;
}
int board_write(uint8_t addr,const uint8_t *data,unsigned n) {
    bus_error=0;int ok=start()&&put(addr<<1);
    for(unsigned i=0;ok&&i<n;i++)ok=put(data[i]);
    stop();return ok&&!bus_error;
}
int board_read(uint8_t addr,uint8_t *data,unsigned n) {
    bus_error=0;int ok=start()&&put((addr<<1)|1);
    for(unsigned i=0;ok&&i<n;i++)ok=get(data+i,i+1<n);
    stop();return ok&&!bus_error;
}
int board_reg_read(uint8_t a,uint8_t r,uint8_t *d,unsigned n) {return read_command(a,&r,1,d,n);}
int board_reg_write(uint8_t a,uint8_t r,uint8_t v) {uint8_t b[]={r,v};return board_write(a,b,2);}
int bq_read(uint8_t r,uint8_t *v) {return board_reg_read(0x6b,r,v,1);}
int bq_write(uint8_t r,uint8_t v) {return board_reg_write(0x6b,r,v);}
int board_ppg_off(void) {
    uint8_t id;
    /* PPG board is optional. If it responds, clear all LED currents and verify shutdown. */
    if(!board_reg_read(0x57,0xff,&id,1))return 1;
    if(id!=0x2b)return 0;
    int ok=board_reg_write(0x57,9,0x80);
    for(uint8_t r=12;r<=15;r++){int a=board_reg_write(0x57,r,0);ok=a&&ok;}
    uint8_t v;if(!board_reg_read(0x57,9,&v,1)||v!=0x80)return 0;
    for(uint8_t r=12;r<=15;r++)if(!board_reg_read(0x57,r,&v,1)||v)return 0;
    return ok;
}

unsigned board_buttons(void){return (!level(13))|((!level(3))<<1);}
