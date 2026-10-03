#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "session.h"
#include "config.h"
static int starts,stops,start_ok=1,stop_ok=1;
int sensors_start(uint8_t m){assert(m>=1&&m<=15);starts++;return start_ok;}
int sensors_stop(void){stops++;return stop_ok;}
static void reset(void){memset(&session,0,sizeof session);starts=stops=0;start_ok=stop_ok=1;}
static void cmd(uint8_t op,uint32_t now,int power){uint8_t p[]={3,op,1,0,3,0,0,0,42,0,0,0};session_control(p,12,now,1,power);}
int main(void){
 reset();cmd(1,0,1);assert(session.state==1&&starts==1);cmd(1,1,1);assert(session.reason==2&&starts==1);
 cmd(3,1000,1);session_tick(5999);assert(session.state==1);session_tick(6000);assert(session.state==0&&session.reason==4&&stops==1);
 reset();cmd(1,0,0);assert(!starts&&session.reason==3);
 reset();start_ok=0;cmd(1,0,1);assert(session.state==2);
 reset();cmd(1,0xfffffff0u,1);session_tick(0x100u);assert(session.state==1);session_tick(0x2000u);assert(session.state==0);
 reset();cmd(1,0,1);cmd(2,1,1);assert(session.state==0&&session.reason==0);
 reset();cmd(1,0,1);stop_ok=0;cmd(2,1,1);assert(session.state==2&&session.reason==6);
 reset();uint8_t config[]={3,4,2,0,50,5,50,15,42,0,0,0};session_control(config,12,0,1,1);assert(!session.reason&&settings.imu_hz==50&&settings.temp_ms==500&&settings.leds==15);
 config[6]=100;session_control(config,12,0,1,1);assert(session.reason==1&&settings.ppg_hz==50);
 config[6]=50;session_control(config,12,0,1,1);cmd(1,0,1);session_control(config,12,0,1,1);assert(session.reason==2);
 puts("PASS: session commands, duplicate Start, charger gate, failed sensor init/stop, keepalive timeout and timer wrap.");
}
