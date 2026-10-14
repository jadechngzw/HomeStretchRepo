/* v0: S140 is sole owner of RADIO, TIMER0 and RTC0. Application uses TIMER2.
   Charging is initialized before enabling BLE; no build-time charger opt-out. */
#include <stdint.h>
#include <string.h>
#include "nrf.h"
#include "nrf_sdm.h"
#include "nrf_soc.h"
#include "ble.h"
#include "board.h"
#include "sensors.h"
#include "session.h"
#include "config.h"
#include "ppg.h"
#include "power/charger_policy.h"
#define APP_RAM 0x20008000u
static uint16_t connection=BLE_CONN_HANDLE_INVALID,att_mtu=23;
static ble_gatts_char_handles_t control_h,status_h,sample_h,telemetry_h;
static uint8_t advertising=BLE_GAP_ADV_SET_HANDLE_NOT_SET,uuid_type;
static uint8_t status_notify,sample_notify,status_pending;
static uint8_t status_value[20];
static int power_ok;
static uint8_t telemetry_notify,telemetry_pending,telemetry_value[20];
static uint16_t presses[2];
static uint8_t tx[128][20];static unsigned tx_head,tx_count;
static void tx_clear(void){session.dropped+=tx_count;tx_head=tx_count=0;}

volatile uint32_t fatal_error;
static void fatal(uint32_t error){fatal_error=error;for(;;){(void)charger_off();(void)sensors_stop();board_delay_us(10000);}}
static void check(uint32_t r){if(r)fatal(r);}
static void softdevice_fault(uint32_t id,uint32_t pc,uint32_t info){(void)pc;(void)info;fatal(id);}
static void p16(uint8_t *p,uint16_t v){p[0]=v;p[1]=v>>8;}
static void p32(uint8_t *p,uint32_t v){p16(p,v);p16(p+2,v>>16);}
static uint32_t notify(uint16_t handle,uint8_t *p){
    uint16_t len=20;ble_gatts_hvx_params_t h={0};h.handle=handle;h.type=BLE_GATT_HVX_NOTIFICATION;h.p_len=&len;h.p_data=p;
    return sd_ble_gatts_hvx(connection,&h);
}
static void update_status(void){
    status_value[0]=3;status_value[1]=session.state;status_value[2]=session.reason;status_value[3]=session.mask;
    p32(status_value+4,session.id);p16(status_value+8,session.request);
    p16(status_value+10,power_ok?(uint16_t)charger_state():2);
    p32(status_value+12,session.generated);p32(status_value+16,session.dropped);
    ble_gatts_value_t value={.len=20,.offset=0,.p_value=status_value};
    check(sd_ble_gatts_value_set(connection,status_h.value_handle,&value));
}
static void sample(uint8_t type,uint32_t ms,const int16_t v[3],int valid){
    uint8_t p[20]={3,type};p32(p+2,session.id);p16(p+6,session.sequence++);p32(p+8,ms);
    for(unsigned i=0;i<3;i++)p16(p+12+2*i,(uint16_t)v[i]);p16(p+18,valid?1:0);
    session.generated++;
    if(connection==BLE_CONN_HANDLE_INVALID||!sample_notify||tx_count==128)session.dropped++;
    else {memcpy(tx[(tx_head+tx_count)%128],p,20);tx_count++;}
}
static void flush_samples(void){
    while(tx_count){
        uint8_t batch[240];unsigned count=(att_mtu-3)/20;if(count>12)count=12;if(count>tx_count)count=tx_count;
        for(unsigned i=0;i<count;i++)memcpy(batch+20*i,tx[(tx_head+i)%128],20);
        uint16_t len=count*20;ble_gatts_hvx_params_t h={0};h.handle=sample_h.value_handle;h.type=BLE_GATT_HVX_NOTIFICATION;h.p_len=&len;h.p_data=batch;
        uint32_t r=sd_ble_gatts_hvx(connection,&h);
        if(r==NRF_ERROR_RESOURCES)break;
        if(r!=NRF_SUCCESS)session.dropped+=count;
        tx_head=(tx_head+count)%128;tx_count-=count;
    }
}
static void telemetry(uint32_t now){
    uint8_t reg=0;int valid=board_reg_read(0x6b,8,&reg,1);
    memset(telemetry_value,0,20);telemetry_value[0]=3;telemetry_value[1]=valid;telemetry_value[2]=reg;
    telemetry_value[3]=power_ok?(uint8_t)charger_state():2;
    p16(telemetry_value+4,presses[0]);p16(telemetry_value+6,presses[1]);p32(telemetry_value+8,now);
    /* Bytes 12..19 reserved. No battery ADC/fuel gauge is wired on this board. */
    ble_gatts_value_t v={.len=20,.p_value=telemetry_value};check(sd_ble_gatts_value_set(connection,telemetry_h.value_handle,&v));
    telemetry_pending=1;
}
static void add_characteristic(uint16_t service,uint16_t short_uuid,int write,int read,int notifications,ble_gatts_char_handles_t *handles){
    ble_gatts_char_md_t cmd={0};cmd.char_props.write=write;cmd.char_props.read=read;cmd.char_props.notify=notifications;
    ble_gatts_attr_md_t md={0},cccd={0};BLE_GAP_CONN_SEC_MODE_SET_OPEN(&md.read_perm);BLE_GAP_CONN_SEC_MODE_SET_OPEN(&md.write_perm);md.vloc=BLE_GATTS_VLOC_STACK;md.vlen=short_uuid==4;
    BLE_GAP_CONN_SEC_MODE_SET_OPEN(&cccd.read_perm);BLE_GAP_CONN_SEC_MODE_SET_OPEN(&cccd.write_perm);cccd.vloc=BLE_GATTS_VLOC_STACK;
    if(notifications)cmd.p_cccd_md=&cccd;
    ble_uuid_t uuid={.uuid=short_uuid,.type=uuid_type};uint8_t initial[20]={0};
    ble_gatts_attr_t attr={.p_uuid=&uuid,.p_attr_md=&md,.init_len=write?12:20,.max_len=short_uuid==4?240:(write?12:20),.p_value=initial};
    check(sd_ble_gatts_characteristic_add(service,&cmd,&attr,handles));
}
static void begin_advertising(void){check(sd_ble_gap_adv_start(advertising,1));}
static void bluetooth_init(void){
    nrf_clock_lf_cfg_t lf={.source=NRF_CLOCK_LF_SRC_RC,.rc_ctiv=16,.rc_temp_ctiv=2,.accuracy=NRF_CLOCK_LF_ACCURACY_500_PPM};
    check(sd_softdevice_enable(&lf,softdevice_fault));
    ble_cfg_t cfg={0};cfg.gap_cfg.role_count_cfg.periph_role_count=1;cfg.gap_cfg.role_count_cfg.central_role_count=0;
    check(sd_ble_cfg_set(BLE_GAP_CFG_ROLE_COUNT,&cfg,APP_RAM));
    memset(&cfg,0,sizeof cfg);cfg.conn_cfg.conn_cfg_tag=1;cfg.conn_cfg.params.gap_conn_cfg.conn_count=1;cfg.conn_cfg.params.gap_conn_cfg.event_length=6;
    check(sd_ble_cfg_set(BLE_CONN_CFG_GAP,&cfg,APP_RAM));
    memset(&cfg,0,sizeof cfg);cfg.conn_cfg.conn_cfg_tag=1;cfg.conn_cfg.params.gatts_conn_cfg.hvn_tx_queue_size=32;
    check(sd_ble_cfg_set(BLE_CONN_CFG_GATTS,&cfg,APP_RAM));
    memset(&cfg,0,sizeof cfg);cfg.conn_cfg.conn_cfg_tag=1;cfg.conn_cfg.params.gatt_conn_cfg.att_mtu=247;
    check(sd_ble_cfg_set(BLE_CONN_CFG_GATT,&cfg,APP_RAM));
    uint32_t ram=APP_RAM;check(sd_ble_enable(&ram));
    ble_gap_conn_sec_mode_t security;BLE_GAP_CONN_SEC_MODE_SET_OPEN(&security);
    const uint8_t name[]="VitalWave-v0";check(sd_ble_gap_device_name_set(&security,name,sizeof(name)-1));
    ble_gap_conn_params_t cp={.min_conn_interval=12,.max_conn_interval=24,.slave_latency=0,.conn_sup_timeout=200};check(sd_ble_gap_ppcp_set(&cp));
    ble_uuid128_t base={{0x00,0xa1,0x81,0x40,0x23,0x5d,0x3b,0x92,0x9d,0x4b,0x4d,0x6e,0x00,0x00,0xfa,0x7b}};
    check(sd_ble_uuid_vs_add(&base,&uuid_type));ble_uuid_t service_uuid={.uuid=1,.type=uuid_type};uint16_t service;
    check(sd_ble_gatts_service_add(BLE_GATTS_SRVC_TYPE_PRIMARY,&service_uuid,&service));
    add_characteristic(service,2,1,0,0,&control_h);add_characteristic(service,3,0,1,1,&status_h);add_characteristic(service,4,0,0,1,&sample_h);add_characteristic(service,5,0,1,1,&telemetry_h);
    update_status();telemetry(board_ms());
    static uint8_t adv[21]={2,1,6,17,7};uint8_t uuid_len=16;check(sd_ble_uuid_encode(&service_uuid,&uuid_len,adv+5));
    static uint8_t scan[32];scan[0]=sizeof(name);scan[1]=9;memcpy(scan+2,name,sizeof(name)-1);
    ble_gap_adv_data_t data={.adv_data={adv,sizeof adv},.scan_rsp_data={scan,sizeof(name)+1}};
    ble_gap_adv_params_t params={0};params.properties.type=BLE_GAP_ADV_TYPE_CONNECTABLE_SCANNABLE_UNDIRECTED;params.primary_phy=BLE_GAP_PHY_1MBPS;params.interval=160;
    check(sd_ble_gap_adv_set_configure(&advertising,&data,&params));begin_advertising();
}
static void events(void){
    static uint32_t buffer[128];uint16_t len=sizeof buffer;uint32_t r;
    while((r=sd_ble_evt_get((uint8_t*)buffer,&len))==NRF_SUCCESS){
        ble_evt_t *e=(ble_evt_t*)buffer;
        switch(e->header.evt_id){
        case BLE_GAP_EVT_CONNECTED:
            connection=e->evt.gap_evt.conn_handle;att_mtu=23;
            {ble_gap_conn_params_t cp={.min_conn_interval=12,.max_conn_interval=24,.slave_latency=0,.conn_sup_timeout=200};(void)sd_ble_gap_conn_param_update(connection,&cp);}
            status_notify=sample_notify=telemetry_notify=0;status_pending=telemetry_pending=1;break;
        case BLE_GAP_EVT_DISCONNECTED:
            if(session.state==1)session_end(5);
            tx_clear();connection=BLE_CONN_HANDLE_INVALID;status_notify=sample_notify=telemetry_notify=0;update_status();begin_advertising();break;
        case BLE_GATTS_EVT_SYS_ATTR_MISSING:check(sd_ble_gatts_sys_attr_set(connection,0,0,0));break;
        case BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST:att_mtu=e->evt.gatts_evt.params.exchange_mtu_request.client_rx_mtu;if(att_mtu>247)att_mtu=247;check(sd_ble_gatts_exchange_mtu_reply(connection,247));break;
        case BLE_GAP_EVT_SEC_PARAMS_REQUEST:check(sd_ble_gap_sec_params_reply(connection,BLE_GAP_SEC_STATUS_PAIRING_NOT_SUPP,0,0));break;
        case BLE_GAP_EVT_PHY_UPDATE_REQUEST:{ble_gap_phys_t p={BLE_GAP_PHY_1MBPS,BLE_GAP_PHY_1MBPS};check(sd_ble_gap_phy_update(connection,&p));break;}
        case BLE_GAP_EVT_DATA_LENGTH_UPDATE_REQUEST:check(sd_ble_gap_data_length_update(connection,0,0));break;
        case BLE_GATTS_EVT_TIMEOUT:(void)sd_ble_gap_disconnect(connection,BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);break;
        case BLE_GATTS_EVT_WRITE:{
            ble_gatts_evt_write_t *w=&e->evt.gatts_evt.params.write;
            if(w->handle==control_h.value_handle){session_control(w->data,w->len,board_ms(),status_notify&&sample_notify,power_ok);update_status();status_pending=1;}
            else if(w->handle==status_h.cccd_handle&&w->len==2){status_notify=w->data[0]&1;status_pending=1;}
            else if(w->handle==sample_h.cccd_handle&&w->len==2)sample_notify=w->data[0]&1;
            else if(w->handle==telemetry_h.cccd_handle&&w->len==2)telemetry_notify=w->data[0]&1;
            if(session.state==1&&(!sample_notify||!status_notify)){session_end(5);status_pending=1;}
            if(!sample_notify&&tx_count)tx_clear();
            break;
        }
        default:break;
        }
        len=sizeof buffer;
    }
    if(r!=NRF_ERROR_NOT_FOUND)check(r);
    uint32_t evt;while(sd_evt_get(&evt)==NRF_SUCCESS){}
}
int main(void){
    board_init();power_ok=charger_init();
    if(!power_ok){session.state=2;session.reason=3;}
    if(!board_ppg_off()||!sensors_stop()){session.state=2;session.reason=6;}
    bluetooth_init();uint32_t power_tick=board_ms(),imu_tick=power_tick,temp_tick=power_tick,temp_began=0;
    int temp_waiting=0;uint32_t temp_retry=0;uint32_t previous_session=0;uint8_t previous_state=session.state;
    uint32_t telemetry_tick=power_tick,ppg_tick=power_tick,ppg_poll=power_tick,ppg_last=power_tick,button_tick=power_tick;
    unsigned button_raw=board_buttons(),button_stable=button_raw;
    for(;;){
        events();uint32_t now=board_ms();
        if((uint32_t)(now-power_tick)>=100){power_tick=now;if(session.state==2)(void)sensors_stop();if(power_ok)power_ok=charger_service();else (void)charger_off();
            if(!power_ok){if(session.state==1)session_end(3);session.state=2;session.reason=3;status_pending=1;}}
        session_tick(now);
        unsigned buttons=board_buttons();
        if(buttons!=button_raw){button_raw=buttons;button_tick=now;}
        if(button_raw!=button_stable&&(uint32_t)(now-button_tick)>=40){
            unsigned edges=button_raw&~button_stable;button_stable=button_raw;
            if(connection!=BLE_CONN_HANDLE_INVALID&&telemetry_notify){for(unsigned i=0;i<2;i++)if(edges&(1u<<i))presses[i]++;telemetry(now);}
        }
        if((uint32_t)(now-telemetry_tick)>=500){telemetry_tick=now;telemetry(now);status_pending=1;}

        if(session.state!=previous_state||session.id!=previous_session){temp_waiting=0;imu_tick=now;temp_tick=now-settings.temp_ms;ppg_tick=ppg_last=now;previous_state=session.state;previous_session=session.id;status_pending=1;}
        if(session.state==1){
            if((session.mask&9)&&(uint32_t)(now-imu_tick)>=1000u/settings.imu_hz){imu_tick+=1000u/settings.imu_hz;if((uint32_t)(now-imu_tick)>=1000u/settings.imu_hz)imu_tick=now;int16_t values[6]={0};int valid=sensors_imu(values);if(session.mask&1)sample(1,now,values+3,valid);if(session.mask&8)sample(2,now,values,valid);}
            if(session.mask&2){
                if(!temp_waiting&&(uint32_t)(now-temp_tick)>=settings.temp_ms){temp_tick=now;temp_began=now;temp_retry=now;temp_waiting=sensors_temp_start();if(!temp_waiting){const int16_t zero[3]={0};sample(3,now,zero,0);}}
                if(temp_waiting&&(uint32_t)(now-temp_began)>=30&&(uint32_t)(now-temp_retry)>=10){temp_retry=now;int16_t values[3]={0};int valid=sensors_temp_read(values,values+1);if(valid||(uint32_t)(now-temp_began)>=60){sample(3,temp_began,values,valid);temp_waiting=0;}}
            }
        }
        if(session.state==1&&(session.mask&4)&&(uint32_t)(now-ppg_poll)>=5){
            ppg_poll=now;unsigned pending=0;
            if(!ppg_pending(&pending)){session_end(6);status_pending=1;}
            /* Limit each pass so BLE, buttons and charger keep being serviced. */
            for(unsigned j=0;j<pending&&j<4&&session.state==1;j++){
                uint32_t v[4]={0};if(!ppg_read(v)){session_end(6);status_pending=1;break;}
                ppg_tick+=1000u/settings.ppg_hz;ppg_last=now;
                for(unsigned c=0;c<4;c++)if(settings.leds&(1u<<c)){
                    int16_t parts[3]={(int16_t)(v[c]&65535),(int16_t)(v[c]>>16),0};sample(4+c,ppg_tick,parts,1);
                }
            }
            if((uint32_t)(now-ppg_last)>1000){session_end(6);status_pending=1;}
        }
        /* Control takes the next available notification slot. The readable status
           is refreshed even when the radio queue is full. Host drains final counts. */
        if(status_pending){update_status();if(connection==BLE_CONN_HANDLE_INVALID||!status_notify||notify(status_h.value_handle,status_value)==NRF_SUCCESS)status_pending=0;}
        if(telemetry_pending&&connection!=BLE_CONN_HANDLE_INVALID&&telemetry_notify&&notify(telemetry_h.value_handle,telemetry_value)==NRF_SUCCESS)telemetry_pending=0;
        if(connection!=BLE_CONN_HANDLE_INVALID&&sample_notify)flush_samples();
        board_delay_us(500);
    }
}
