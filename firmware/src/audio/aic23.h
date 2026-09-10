/* TLV320AIC23B codec driver (I2C control, I2S slave audio) */
#ifndef AIC23_H
#define AIC23_H

#include <stdint.h>
#include <stdbool.h>
#include "stm32h7xx_hal.h"

/* register addresses (7-bit) */
#define AIC23_LLINEIN   0x00
#define AIC23_RLINEIN   0x01
#define AIC23_LHPOUT    0x02
#define AIC23_RHPOUT    0x03
#define AIC23_ANAPATH   0x04
#define AIC23_DIGPATH   0x05
#define AIC23_POWER     0x06
#define AIC23_DIGIF     0x07
#define AIC23_SRATE     0x08
#define AIC23_DIGACT    0x09
#define AIC23_RESET     0x0F

bool aic23_init(I2C_HandleTypeDef *i2c);
bool aic23_write(uint8_t reg, uint16_t val);       /* 9-bit value */
void aic23_set_line_in_gain(uint8_t gain_0_31, bool both);
void aic23_mute_output(bool mute);

#endif
