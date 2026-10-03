#ifndef VW_SESSION_H
#define VW_SESSION_H
#include <stdint.h>
typedef struct {uint8_t state,reason,mask;uint32_t id,last_ping;uint16_t request,sequence;uint32_t generated,dropped;} Session;
extern Session session;
void session_control(const uint8_t *p,unsigned n,uint32_t now,int subscribed,int charger_ok);
void session_end(uint8_t reason);
void session_tick(uint32_t now);
#endif
