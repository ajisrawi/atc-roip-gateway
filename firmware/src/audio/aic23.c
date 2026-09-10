#include "aic23.h"
#include "../board.h"

static I2C_HandleTypeDef *hi2c;

bool aic23_write(uint8_t reg, uint16_t val)
{
    /* AIC23 control word: 7-bit register address + 9-bit data */
    uint8_t buf[2] = {
        (uint8_t)((reg << 1) | ((val >> 8) & 1)),
        (uint8_t)(val & 0xFF),
    };
    return HAL_I2C_Master_Transmit(hi2c, CODEC_I2C_ADDR, buf, 2, 20)
           == HAL_OK;
}

bool aic23_init(I2C_HandleTypeDef *i2c)
{
    hi2c = i2c;
    bool ok = true;
    ok &= aic23_write(AIC23_RESET, 0x000);
    HAL_Delay(2);
    /* power: everything on except mic + xtal-out (line-in path only) */
    ok &= aic23_write(AIC23_POWER, 0x002);     /* MIC powered down       */
    /* analog path: DAC selected, line inputs to ADC, bypass off        */
    ok &= aic23_write(AIC23_ANAPATH, 0x012);   /* DACSEL=1, INSEL=line   */
    /* digital path: de-emphasis off, no soft mute, HPF enabled         */
    ok &= aic23_write(AIC23_DIGPATH, 0x000);
    /* digital IF: I2S, 16-bit, slave mode                              */
    ok &= aic23_write(AIC23_DIGIF, 0x002);
    /* sample rate: 8 kHz ADC/DAC, normal mode, MCLK = 2.048 MHz(256fs) */
    ok &= aic23_write(AIC23_SRATE, 0x00C);     /* SR=0011, BOSR=0        */
    /* unmute line inputs, 0 dB */
    ok &= aic23_write(AIC23_LLINEIN, 0x017);
    ok &= aic23_write(AIC23_RLINEIN, 0x017);
    /* headphone outs (unused, leave low) */
    ok &= aic23_write(AIC23_LHPOUT, 0x000);
    ok &= aic23_write(AIC23_RHPOUT, 0x000);
    /* activate digital interface */
    ok &= aic23_write(AIC23_DIGACT, 0x001);
    return ok;
}

void aic23_set_line_in_gain(uint8_t g, bool both)
{
    uint16_t v = (uint16_t)(g & 0x1F);
    aic23_write(AIC23_LLINEIN, v);
    if (both)
        aic23_write(AIC23_RLINEIN, v);
}

void aic23_mute_output(bool mute)
{
    aic23_write(AIC23_DIGPATH, mute ? 0x008 : 0x000);
}
