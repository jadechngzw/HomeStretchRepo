#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include "ppg.h"
#include "config.h"
static uint8_t regs[256];static int failure;static unsigned bytes_read;
void board_delay_us(uint32_t n){(void)n;}
int board_ppg_off(void){regs[9]=0x80;for(int i=12;i<16;i++)regs[i]=0;return 1;}
int board_reg_write(uint8_t addr,uint8_t reg,uint8_t v){assert(addr==0x57);if(failure==reg)return 0;regs[reg]=reg==9&&v==0x40?0:v;return 1;}
int board_reg_read(uint8_t addr,uint8_t reg,uint8_t *out,unsigned n){
 assert(addr==0x57);if(failure==reg)return 0;
 if(reg==7){bytes_read=n;for(unsigned i=0;i<n/3;i++){out[3*i]=7;out[3*i+1]=0xff;out[3*i+2]=0xff-i;}return 1;}
 memcpy(out,regs+reg,n);return 1;
}
static void reset(void){memset(regs,0,sizeof regs);regs[255]=0x2b;failure=-1;}
int main(void){
 reset();assert(ppg_start(15,50));assert(regs[19]==0x21&&regs[20]==0x43&&regs[10]==0x22);
 for(int i=12;i<16;i++)assert(regs[i]==10);
 uint32_t v[4]={0};assert(ppg_read(v)&&bytes_read==12);assert(v[0]==524287&&v[3]==524284);
 unsigned pending;regs[4]=2;regs[6]=30;assert(ppg_pending(&pending)&&pending==4);
 regs[5]=1;assert(!ppg_pending(&pending));regs[5]=0;regs[0]=0x20;assert(!ppg_pending(&pending));
 assert(ppg_stop()&&regs[9]==0x80);for(int i=12;i<16;i++)assert(!regs[i]);
 reset();assert(ppg_start(4,100));assert(regs[19]==3&&regs[20]==0&&regs[14]==10&&regs[12]==0&&regs[10]==0x26);
 memset(v,0,sizeof v);assert(ppg_read(v)&&bytes_read==3&&v[2]==524287&&!v[0]);assert(ppg_stop());
 reset();failure=19;assert(!ppg_start(15,50));assert(regs[9]==0x80);for(int i=12;i<16;i++)assert(!regs[i]);
 reset();regs[255]=0;assert(!ppg_start(4,50));
 puts("PASS: PPG slot order, low currents, FIFO rollover/overflow, optical fault, full 19-bit samples, failure shutdown.");
}
