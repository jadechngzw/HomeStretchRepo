#include "config.h"
Settings settings={25,1000,50,0};
int settings_apply(uint32_t p){
    unsigned i=p&255,t=(p>>8)&255,h=(p>>16)&255,l=p>>24;
    if((i!=10&&i!=25&&i!=50)||(t!=5&&t!=10&&t!=20)||(h!=50&&h!=100)||l>15)return 0;
    /* Bound the multi-colour notification load. */
    if((l&(l-1))&&h!=50)return 0;
    settings=(Settings){i,t*100,h,l};return 1;
}
