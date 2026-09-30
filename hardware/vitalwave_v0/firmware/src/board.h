#include <stdint.h>
void board_init(void);
uint32_t board_ms(void);
void board_delay_us(uint32_t n);
int board_write(uint8_t addr,const uint8_t *data,unsigned n);
int board_read(uint8_t addr,uint8_t *data,unsigned n);
int board_reg_read(uint8_t addr,uint8_t reg,uint8_t *data,unsigned n);
int board_reg_write(uint8_t addr,uint8_t reg,uint8_t value);
int board_ppg_off(void);

unsigned board_buttons(void);
