/* ATC RoIP Gateway - board pin map (schematic rev A)
 *
 * MCU: STM32H743VIT6 (LQFP-100), HSE 25 MHz crystal.
 */
#ifndef BOARD_H
#define BOARD_H

#include "stm32h7xx_hal.h"

/* ---- RMII to LAN8742A --------------------------------------------------- */
#define ETH_REF_CLK_PIN    GPIO_PIN_1   /* PA1  */
#define ETH_MDIO_PIN       GPIO_PIN_2   /* PA2  */
#define ETH_MDC_PIN        GPIO_PIN_1   /* PC1  */
#define ETH_CRS_DV_PIN     GPIO_PIN_7   /* PA7  */
#define ETH_RXD0_PIN       GPIO_PIN_4   /* PC4  */
#define ETH_RXD1_PIN       GPIO_PIN_5   /* PC5  */
#define ETH_TX_EN_PIN      GPIO_PIN_11  /* PB11 */
#define ETH_TXD0_PIN       GPIO_PIN_12  /* PB12 */
#define ETH_TXD1_PIN       GPIO_PIN_13  /* PB13 */
#define ETH_NRST_PORT      GPIOE        /* PHY hardware reset */
#define ETH_NRST_PIN       GPIO_PIN_10  /* PE10 */
#define ETH_PHY_ADDR       0            /* RXER/PHYAD0 floating -> 0 */

/* ---- SAI1 to TLV320AIC23B ----------------------------------------------- */
#define SAI_MCLK_PIN       GPIO_PIN_2   /* PE2  SAI1_MCLK_A */
#define SAI_BCLK_PIN       GPIO_PIN_5   /* PE5  SAI1_SCK_A  */
#define SAI_FS_PIN         GPIO_PIN_4   /* PE4  SAI1_FS_A   */
#define SAI_SD_OUT_PIN     GPIO_PIN_6   /* PE6  SAI1_SD_A -> codec DIN  */
#define SAI_SD_IN_PIN      GPIO_PIN_3   /* PE3  SAI1_SD_B <- codec DOUT */

/* ---- Codec control ------------------------------------------------------ */
#define CODEC_I2C          I2C1         /* PB6 SCL / PB7 SDA */
#define CODEC_I2C_ADDR     (0x1A << 1)  /* CS pin low        */

/* ---- Radio discrete I/O (through PC817 optos) --------------------------- */
#define PTT_VHF_PORT       GPIOD
#define PTT_VHF_PIN        GPIO_PIN_8   /* PD8, high = key VHF PTT  */
#define PTT_HF_PORT        GPIOD
#define PTT_HF_PIN         GPIO_PIN_9   /* PD9, high = key HF PTT   */
#define COR_VHF_PORT       GPIOD
#define COR_VHF_PIN        GPIO_PIN_10  /* PD10, low = VHF squelch open */
#define COR_HF_PORT        GPIOD
#define COR_HF_PIN         GPIO_PIN_11  /* PD11, low = HF squelch open  */

/* ---- Status LEDs / console ---------------------------------------------- */
#define LED1_PORT GPIOD
#define LED1_PIN  GPIO_PIN_12           /* link/session */
#define LED2_PORT GPIOD
#define LED2_PIN  GPIO_PIN_13           /* VHF activity */
#define LED3_PORT GPIOD
#define LED3_PIN  GPIO_PIN_14           /* HF activity  */
#define CONSOLE_UART       USART1       /* PA9 TX / PA10 RX, 115200 8N1 */

#endif /* BOARD_H */
