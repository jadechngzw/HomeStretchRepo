#include "charger_policy.h"
ChargerDiagnostic charger_diag;
/* Preserve first failure before shutdown changes the registers.
   1=read failure, 2=write failure, 3=readback/profile mismatch,
   4=historical fault, 5=current fault, 6=wrong part ID. */
void charger_record_error(uint8_t c,uint8_t r,uint8_t a,uint8_t e,uint8_t m) {
    if(!charger_diag.code)charger_diag=(ChargerDiagnostic){c,r,a,e,m};
}
static int read_checked(uint8_t r,uint8_t *v) {
    if(bq_read(r,v))return 1;
    charger_record_error(1,r,0,0,0);return 0;
}
static int update(uint8_t reg,uint8_t mask,uint8_t value) {
    uint8_t old,got;
    if(!read_checked(reg,&old))return 0;
    uint8_t desired=(old&~mask)|(value&mask);
    if(!bq_write(reg,desired)){charger_record_error(2,reg,0,desired,255);return 0;}
    if(!read_checked(reg,&got))return 0;
    if(got!=desired){charger_record_error(3,reg,got,desired,255);return 0;}
    return 1;
}
int charger_off(void) {
    int a=update(1,0x70,0);
    int b=update(2,0x3f,0);
    return a&&b;
}
static int profile_ok(int enabled, int check_input) {
    const uint8_t masks[]={0x9f,0x30,0x3f,0xff,0xf8,0xbe};
    const uint8_t expected[]={4,enabled?0x10:0,4,0,0x38,0x88};
    for(uint8_t r=check_input?0:1;r<6;r++) {
        uint8_t actual;if(!read_checked(r,&actual))return 0;
        if((actual&masks[r])!=expected[r]) {
            charger_record_error(3,r,actual,expected[r],masks[r]);return 0;
        }
    }
    return 1;
}
static int faults_ok(int check_history) {
    uint8_t historical,current;
    if(!read_checked(9,&historical)||!read_checked(9,&current))return 0;
    if(current){charger_record_error(5,9,current,0,255);return 0;}
    if(check_history&&historical){charger_record_error(4,9,historical,0,255);return 0;}
    return 1;
}
static int state=-1;
static unsigned stable;
static uint8_t source;
int charger_state(void) { return state; }
static int configure(void) {
    if(!update(1,0x70,0))return 0;
    if(!update(5,0xbe,0x88))return 0; /* watchdog off; 5h timer, termination, 90C */
    if(!update(2,0x3f,4))return 0; /* 240mA */
    if(!update(3,0xff,0))return 0; /* 60mA precharge and termination */
    if(!update(4,0xf8,0x38))return 0; /* 4.080V */
    return profile_ok(0,0);
}
int charger_init(void) {
    uint8_t id;
    charger_diag=(ChargerDiagnostic){0};state=-1;stable=0;source=0;
    /* First transaction disables charging, even before identity checking. */
    if(!charger_off())goto fail;
    if(!read_checked(0x0b,&id))goto fail;
    if(((id>>3)&15)!=2){charger_record_error(6,0x0b,id,0x10,0x78);goto fail;}
    if(!configure()||!faults_ok(0))goto fail;
    state=0;return 1;
fail:
    (void)charger_off();return 0;
}
/* Call no faster than every 100ms. State 0=waiting disabled, 1=enabled,
   -1=latched failure. Input-limit changes are tolerated ONLY while disabled. */
int charger_service(void) {
    uint8_t status,after;
    if(state<0)return 0;
    if(!read_checked(8,&status))goto fail;
    uint8_t detected=(status>>5)&7;
    int good=(status&4)&&(detected==1||detected==3);
    if(!good || (state==1 && detected!=source)) {
        if(!update(1,0x70,0))goto fail;
        state=0;stable=0;source=detected;
    }
    if(!profile_ok(state==1,state==1)||!faults_ok(1))goto fail;
    if(state==1 || !good)return 1;
    if(source!=detected){source=detected;stable=0;}
    if(++stable<6)return 1;
    /* PG_STAT and VBUS_STAT confirm source detection completed. Reapply the
       input limit AFTER detection, then read back all settings before enable. */
    if(!update(0,0x9f,4)||!profile_ok(0,1))goto fail;
    if(!read_checked(8,&after))goto fail;
    if((after&0xe4)!=(status&0xe4)){stable=0;return 1;}
    if(!faults_ok(1)||!update(1,0x70,0x10))goto fail;
    state=1;
    if(!profile_ok(1,1)||!faults_ok(1))goto fail;
    return 1;
fail:
    state=-1;(void)charger_off();return 0;
}
