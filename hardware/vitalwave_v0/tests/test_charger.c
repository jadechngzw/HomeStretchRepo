#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "power/charger_policy.h"
static uint8_t regs[12];static int fail_reg=-1,enabled=0;
int bq_read(uint8_t r,uint8_t *v){if(r==fail_reg)return 0;*v=regs[r];return 1;}
int bq_write(uint8_t r,uint8_t v){
 if(r==fail_reg)return 0;
 if(r==1&&(v&0x10)) {
   assert((regs[0]&0x9f)==4);assert(!(regs[1]&0x10));assert((regs[2]&63)==4);
   assert(regs[3]==0);assert((regs[4]&0xf8)==0x38);
   assert((regs[5]&0xbe)==0x88);enabled++;
 }
 regs[r]=v;return 1;
}
static void reset(void){memset(regs,0,sizeof regs);regs[0]=0x17;regs[0xb]=0x10;regs[1]=0x1a;regs[2]=0xa2;regs[3]=0x22;regs[4]=0x58;regs[5]=0x9f;fail_reg=-1;enabled=0;}
static void plug(void){regs[0]=0x17;regs[8]=0x64;}
static void settle(void){for(int n=0;n<6;n++)assert(charger_service());}
int main(void){
 reset();assert(charger_init());assert(!enabled);assert(!(regs[1]&0x10));
 for(int n=0;n<20;n++)assert(charger_service());assert(!enabled);
 plug();for(int n=0;n<5;n++){assert(charger_service());assert(!enabled);}
 assert(charger_service());assert(enabled==1);assert(charger_state()==1);
 assert((regs[0]&31)==4);assert((regs[2]&63)==4);
 regs[8]=0;assert(charger_service());assert(!(regs[1]&0x10));
 plug();settle();assert(enabled==2);
 regs[2]=0xa2;assert(!charger_service());assert(!(regs[1]&0x10));
 assert(charger_diag.code==3&&charger_diag.reg==2);assert(!charger_service());
 reset();assert(charger_init());plug();settle();regs[0]=0x17;
 assert(!charger_service());assert(!(regs[1]&0x10)); /* drift while enabled is still fatal */
 for(int r=0;r<=5;r++){reset();assert(charger_init());plug();fail_reg=r;for(int n=0;n<7;n++)charger_service();assert(!enabled);assert(charger_state()==-1);}
 reset();regs[9]=0x10;assert(!charger_init());assert(!enabled);
 reset();regs[0xb]=0;assert(!charger_init());assert(!enabled);
 reset();assert(charger_init());plug();regs[8]=0x60;settle();assert(!enabled); /* no PG */
 reset();assert(charger_init());plug();for(int n=0;n<4;n++)assert(charger_service());regs[8]=0;assert(charger_service());plug();for(int n=0;n<5;n++){assert(charger_service());assert(!enabled);}assert(charger_service());assert(enabled==1);
 reset();assert(charger_init());plug();regs[9]=0x80;assert(!charger_service());assert(!enabled);
 puts("PASS: battery-only OFF, insertion rewrites input limit before enable, unplug/replug, debounce, no-PG, register drift, I2C failures, charger faults, identity failure.");
}
