#include "session.h"
#include "sensors.h"
#include "config.h"
Session session;
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
void session_end(uint8_t reason){int ok=sensors_stop();session.state=ok?0:2;session.reason=ok?reason:6;}
void session_control(const uint8_t *p,unsigned n,uint32_t now,int subscribed,int charger_ok){
    if(n!=12||p[0]!=3){session.reason=1;return;}
    session.request=(uint16_t)p[2]|((uint16_t)p[3]<<8);
    uint32_t arg=u32(p+4),id=u32(p+8);
    if(!id||!session.request){session.reason=1;return;}
    if(p[1]==4){
        if(session.state!=0){session.reason=2;return;}
        session.reason=settings_apply(arg)?0:1;return;
    }
    if(p[1]==1){
        if(session.state==1){session.reason=2;return;}
        if(!charger_ok||session.state==2){session.reason=3;return;}
        if(!subscribed||arg<1||arg>15||((arg&4)&&!settings.leds)){session.reason=1;return;}
        if(!sensors_start(arg)){session.state=2;session.reason=6;return;}
        session.id=id;session.mask=arg;session.generated=session.dropped=0;session.sequence=0;
        session.last_ping=now;session.state=1;session.reason=0;
    }else if(p[1]==2&&id==session.id){session_end(0);}
    else if(p[1]==3&&id==session.id&&session.state==1){session.last_ping=now;session.reason=0;}
    else session.reason=1;
}
void session_tick(uint32_t now){if(session.state==1&&(uint32_t)(now-session.last_ping)>=5000)session_end(4);}
