/* ATC RoIP Gateway - main entry.
 *
 * Superloop architecture: interrupts move audio (SAI DMA) and packets
 * (Ethernet DMA -> lwIP); the loop runs housekeeping.
 */
#include "stm32h7xx_hal.h"
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/timeouts.h"
#include "lwip/dhcp.h"
#include "netif/ethernet.h"

#include "board.h"
#include "app_config.h"
#include "audio/aic23.h"
#include "audio/sai_stream.h"
#include "net/roip_chan.h"
#include "ed137/sip_mini.h"

/* ethernetif_init comes from the STM32CubeH7 lwIP glue (third_party) */
extern err_t ethernetif_init(struct netif *netif);
extern void ethernetif_input(struct netif *netif);

static struct netif gnetif;
static I2C_HandleTypeDef hi2c1;
static UART_HandleTypeDef huart1;
static roip_chan_t chans[CH_COUNT];

/* ------------------------------------------------------------- clocks */
static void SystemClock_Config(void)
{
    /* HSE 25 MHz -> PLL1 -> 480 MHz core; PLL3 -> SAI kernel clock
     * producing 2.048 MHz MCLK for the codec (256 * 8 kHz).
     * Full HAL RCC init generated per STM32CubeMX for STM32H743VIT6;
     * see docs/02-design-spec.md for the clock tree. */
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE0);
    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 5;      /* 25/5 = 5 MHz    */
    osc.PLL.PLLN = 192;    /* 5*192 = 960 MHz */
    osc.PLL.PLLP = 2;      /* 480 MHz sysclk  */
    osc.PLL.PLLQ = 4;
    osc.PLL.PLLR = 2;
    osc.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
    osc.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK |
                    RCC_CLOCKTYPE_D1PCLK1 | RCC_CLOCKTYPE_PCLK1 |
                    RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_D3PCLK1;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.SYSCLKDivider = RCC_SYSCLK_DIV1;
    clk.AHBCLKDivider = RCC_HCLK_DIV2;
    clk.APB1CLKDivider = RCC_APB1_DIV2;
    clk.APB2CLKDivider = RCC_APB2_DIV2;
    clk.APB3CLKDivider = RCC_APB3_DIV2;
    clk.APB4CLKDivider = RCC_APB4_DIV2;
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4);
}

/* ------------------------------------------------------------- gpio */
static void gpio_init(void)
{
    GPIO_InitTypeDef g = {0};
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();

    g.Pin = PTT_VHF_PIN | PTT_HF_PIN | LED1_PIN | LED2_PIN | LED3_PIN;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOD, &g);
    HAL_GPIO_WritePin(GPIOD, PTT_VHF_PIN | PTT_HF_PIN, GPIO_PIN_RESET);

    g.Pin = COR_VHF_PIN | COR_HF_PIN;
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOD, &g);

    g.Pin = ETH_NRST_PIN;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(ETH_NRST_PORT, &g);
    HAL_GPIO_WritePin(ETH_NRST_PORT, ETH_NRST_PIN, GPIO_PIN_SET);
}

static void i2c_init(void)
{
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_I2C1_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    g.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    g.Mode = GPIO_MODE_AF_OD;
    g.Pull = GPIO_NOPULL;      /* external 4.7k pull-ups R3/R4 */
    g.Speed = GPIO_SPEED_FREQ_LOW;
    g.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &g);
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x10C0ECFF;    /* ~100 kHz from 100 MHz kernel */
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    HAL_I2C_Init(&hi2c1);
}

static void uart_init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_USART1_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    g.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    g.Mode = GPIO_MODE_AF_PP;
    g.Alternate = GPIO_AF7_USART1;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &g);
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    HAL_UART_Init(&huart1);
}

/* ------------------------------------------------- audio frame callback */
static void audio_frame(const int16_t *rx, int16_t *tx)
{
    /* de-interleave: L = VHF, R = HF */
    static int16_t cap[CH_COUNT][CFG_FRAME_SAMPLES];
    static int16_t play[CH_COUNT][CFG_FRAME_SAMPLES];
    for (int i = 0; i < CFG_FRAME_SAMPLES; i++) {
        cap[CH_VHF][i] = rx[2 * i];
        cap[CH_HF][i] = rx[2 * i + 1];
    }
    uint32_t now = HAL_GetTick();
    for (int c = 0; c < CH_COUNT; c++)
        roip_chan_audio_frame(&chans[c], cap[c], play[c], now);
    for (int i = 0; i < CFG_FRAME_SAMPLES; i++) {
        tx[2 * i] = play[CH_VHF][i];
        tx[2 * i + 1] = play[CH_HF][i];
    }
    HAL_GPIO_WritePin(LED2_PORT, LED2_PIN,
                      chans[CH_VHF].cor_active || chans[CH_VHF].ptt_keyed
                      ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED3_PORT, LED3_PIN,
                      chans[CH_HF].cor_active || chans[CH_HF].ptt_keyed
                      ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* ------------------------------------------------- SIP session callback */
static void on_session(roip_channel_id_t id, bool up,
                       const ip_addr_t *peer, uint16_t rtp_port)
{
    if (up)
        roip_chan_set_peer(&chans[id], peer, rtp_port);
    roip_chan_session(&chans[id], up);
    HAL_GPIO_WritePin(LED1_PORT, LED1_PIN,
                      (chans[CH_VHF].session_up || chans[CH_HF].session_up)
                      ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    SCB_EnableICache();
    SCB_EnableDCache();
    gpio_init();
    i2c_init();
    uart_init();

    /* PHY hardware reset pulse */
    HAL_GPIO_WritePin(ETH_NRST_PORT, ETH_NRST_PIN, GPIO_PIN_RESET);
    HAL_Delay(10);
    HAL_GPIO_WritePin(ETH_NRST_PORT, ETH_NRST_PIN, GPIO_PIN_SET);
    HAL_Delay(50);

    /* network */
    lwip_init();
    ip4_addr_t ip, mask, gw;
    ip4_addr_set_zero(&ip);
    ip4_addr_set_zero(&mask);
    ip4_addr_set_zero(&gw);
#if !CFG_USE_DHCP
    ip4addr_aton(CFG_STATIC_IP, &ip);
    ip4addr_aton(CFG_STATIC_MASK, &mask);
    ip4addr_aton(CFG_STATIC_GW, &gw);
#endif
    netif_add(&gnetif, &ip, &mask, &gw, NULL, ethernetif_init,
              ethernet_input);
    netif_set_default(&gnetif);
    netif_set_up(&gnetif);
#if CFG_USE_DHCP
    dhcp_start(&gnetif);
#endif

    /* audio */
    aic23_init(&hi2c1);
    sai_stream_init(audio_frame);
    sai_stream_start();

    /* RoIP channels */
    roip_chan_init(&chans[CH_VHF], CH_VHF, CFG_RTP_PORT_VHF);
    roip_chan_init(&chans[CH_HF], CH_HF, CFG_RTP_PORT_HF);
#if CFG_SIP_ENABLE
    sip_init(on_session);
#else
    ip_addr_t peer;
    ipaddr_aton(CFG_STATIC_PEER_IP, &peer);
    roip_chan_set_peer(&chans[CH_VHF], &peer, CFG_STATIC_PEER_PORT_VHF);
    roip_chan_set_peer(&chans[CH_HF], &peer, CFG_STATIC_PEER_PORT_HF);
    roip_chan_session(&chans[CH_VHF], true);
    roip_chan_session(&chans[CH_HF], true);
#endif

    uint32_t last_poll = 0;
    for (;;) {
        ethernetif_input(&gnetif);
        sys_check_timeouts();
        uint32_t now = HAL_GetTick();
        if (now != last_poll) {
            last_poll = now;
            roip_chan_poll(&chans[CH_VHF], now);
            roip_chan_poll(&chans[CH_HF], now);
#if CFG_SIP_ENABLE
            sip_poll(now);
#endif
        }
    }
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}
