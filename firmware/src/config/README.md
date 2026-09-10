# Board config files (copy-and-adapt from STM32CubeH7)

This directory holds the four project-config files that STM32CubeH7 provides
as templates. Copy them from the Cube tree after cloning it and adjust:

| File | Copy from | Adjust |
|---|---|---|
| `stm32h7xx_hal_conf.h` | `Drivers/STM32H7xx_HAL_Driver/Inc/stm32h7xx_hal_conf_template.h` | enable HAL_ETH/SAI/I2C/UART/DMA modules, HSE_VALUE 25 MHz |
| `lwipopts.h` | any H7 lwIP example (`Projects/NUCLEO-H743ZI/Applications/LwIP/...`) | `NO_SYS 1`, `LWIP_DHCP 1`, UDP enabled, no TCP needed |
| `ethernetif.c/.h` | same lwIP example | RMII pins per `src/board.h` (PA1/PA2/PA7, PC1/PC4/PC5, PB11/PB12/PB13), PHY address 0 (LAN8742) |
| `STM32H743VITx_FLASH.ld` | `Projects/.../STM32H743ZITX_FLASH.ld` | add a `.dma_buf` section in D2 SRAM (0x30000000) for the SAI/ETH DMA buffers |

The NUCLEO-H743ZI lwIP example is the closest starting point — same MCU
family, same LAN8742 PHY, same RMII wiring except the TX_EN/TXD0/TXD1 port
choices, which `src/board.h` documents.
