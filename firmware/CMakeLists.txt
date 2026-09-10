cmake_minimum_required(VERSION 3.20)
project(atc-roip-gw C ASM)

set(CUBE ${CMAKE_CURRENT_SOURCE_DIR}/third_party/STM32CubeH7)
if(NOT EXISTS ${CUBE})
    message(FATAL_ERROR
        "STM32CubeH7 not found. Run:\n"
        "  git clone --depth 1 "
        "https://github.com/STMicroelectronics/STM32CubeH7 "
        "third_party/STM32CubeH7")
endif()

set(MCU_FLAGS -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard)

add_executable(${PROJECT_NAME}
    src/main.c
    src/ed137/rtp_ed137.c
    src/ed137/sip_mini.c
    src/ed137/g711.c
    src/audio/aic23.c
    src/audio/sai_stream.c
    src/net/roip_chan.c
    src/dsp/voxagc.c
    # --- ST HAL (add further hal modules as needed) ---
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_cortex.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_rcc.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_rcc_ex.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_pwr.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_pwr_ex.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_gpio.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_dma.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_i2c.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_uart.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_sai.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_eth.c
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_flash.c
    # --- CMSIS startup ---
    ${CUBE}/Drivers/CMSIS/Device/ST/STM32H7xx/Source/Templates/gcc/startup_stm32h743xx.s
    ${CUBE}/Drivers/CMSIS/Device/ST/STM32H7xx/Source/Templates/system_stm32h7xx.c
    # --- lwIP core (NO_SYS=1) ---
    # add ${CUBE}/Middlewares/Third_Party/LwIP sources per its filelists;
    # simplest: include its src/core, src/core/ipv4, src/netif/ethernet.c
)

file(GLOB LWIP_CORE
    ${CUBE}/Middlewares/Third_Party/LwIP/src/core/*.c
    ${CUBE}/Middlewares/Third_Party/LwIP/src/core/ipv4/*.c
    ${CUBE}/Middlewares/Third_Party/LwIP/src/netif/ethernet.c)
target_sources(${PROJECT_NAME} PRIVATE ${LWIP_CORE})

target_include_directories(${PROJECT_NAME} PRIVATE
    src
    src/config          # stm32h7xx_hal_conf.h, lwipopts.h, ethernetif glue
    ${CUBE}/Drivers/STM32H7xx_HAL_Driver/Inc
    ${CUBE}/Drivers/CMSIS/Device/ST/STM32H7xx/Include
    ${CUBE}/Drivers/CMSIS/Include
    ${CUBE}/Middlewares/Third_Party/LwIP/src/include)

target_compile_definitions(${PROJECT_NAME} PRIVATE
    STM32H743xx USE_HAL_DRIVER HSE_VALUE=25000000 NO_SYS=1)

target_compile_options(${PROJECT_NAME} PRIVATE
    ${MCU_FLAGS} -Og -g3 -ffunction-sections -fdata-sections -Wall)

target_link_options(${PROJECT_NAME} PRIVATE
    ${MCU_FLAGS} -T${CMAKE_CURRENT_SOURCE_DIR}/src/config/STM32H743VITx_FLASH.ld
    -Wl,--gc-sections -specs=nano.specs -specs=nosys.specs
    -Wl,-Map=${PROJECT_NAME}.map)

add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}>
            ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${PROJECT_NAME}>
            ${PROJECT_NAME}.hex)
