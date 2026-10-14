#include <stdint.h>
int bq_read(uint8_t reg,uint8_t *v);
int bq_write(uint8_t reg,uint8_t v);
int charger_init(void);
int charger_service(void);
int charger_state(void);
int charger_off(void);

typedef struct { uint8_t code,reg,actual,expected,mask; } ChargerDiagnostic;
extern ChargerDiagnostic charger_diag;
void charger_record_error(uint8_t code,uint8_t reg,uint8_t actual,uint8_t expected,uint8_t mask);
