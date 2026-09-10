#include "sai_stream.h"
#include "board.h"
#include <string.h>

/* stereo interleaved, double-buffered (2 halves of one 20 ms frame each) */
#define HALF_SAMPLES   (CFG_FRAME_SAMPLES * 2)          /* L+R           */
#define BUF_SAMPLES    (HALF_SAMPLES * 2)               /* two halves    */

static SAI_HandleTypeDef hsai_tx;      /* SAI1 Block A, master TX       */
static SAI_HandleTypeDef hsai_rx;      /* SAI1 Block B, sync slave RX   */
static DMA_HandleTypeDef hdma_tx, hdma_rx;
static sai_frame_cb frame_cb;

/* DMA buffers must live in a non-cached / cache-managed region on H7   */
__attribute__((section(".dma_buf"), aligned(32)))
static int16_t tx_buf[BUF_SAMPLES];
__attribute__((section(".dma_buf"), aligned(32)))
static int16_t rx_buf[BUF_SAMPLES];

static void sai_gpio_init(void)
{
    GPIO_InitTypeDef g = {0};
    __HAL_RCC_GPIOE_CLK_ENABLE();
    g.Pin = SAI_MCLK_PIN | SAI_BCLK_PIN | SAI_FS_PIN | SAI_SD_OUT_PIN |
            SAI_SD_IN_PIN;
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    g.Alternate = GPIO_AF6_SAI1;
    HAL_GPIO_Init(GPIOE, &g);
}

bool sai_stream_init(sai_frame_cb cb)
{
    frame_cb = cb;
    sai_gpio_init();
    __HAL_RCC_SAI1_CLK_ENABLE();
    __HAL_RCC_DMA1_CLK_ENABLE();

    /* Block A: master transmit, I2S, 16-bit, 8 kHz, MCLK out 256*Fs */
    hsai_tx.Instance = SAI1_Block_A;
    hsai_tx.Init.AudioMode = SAI_MODEMASTER_TX;
    hsai_tx.Init.Synchro = SAI_ASYNCHRONOUS;
    hsai_tx.Init.OutputDrive = SAI_OUTPUTDRIVE_ENABLE;
    hsai_tx.Init.NoDivider = SAI_MASTERDIVIDER_ENABLE;
    hsai_tx.Init.FIFOThreshold = SAI_FIFOTHRESHOLD_1QF;
    hsai_tx.Init.AudioFrequency = SAI_AUDIO_FREQUENCY_8K;
    hsai_tx.Init.MonoStereoMode = SAI_STEREOMODE;
    hsai_tx.Init.Mckdiv = 0;    /* HAL computes from PLL when 0 */
    if (HAL_SAI_InitProtocol(&hsai_tx, SAI_I2S_STANDARD,
                             SAI_PROTOCOL_DATASIZE_16BIT, 2) != HAL_OK)
        return false;

    /* Block B: synchronous slave receive */
    hsai_rx.Instance = SAI1_Block_B;
    hsai_rx.Init = hsai_tx.Init;
    hsai_rx.Init.AudioMode = SAI_MODESLAVE_RX;
    hsai_rx.Init.Synchro = SAI_SYNCHRONOUS;
    if (HAL_SAI_InitProtocol(&hsai_rx, SAI_I2S_STANDARD,
                             SAI_PROTOCOL_DATASIZE_16BIT, 2) != HAL_OK)
        return false;

    /* DMA: circular, half/full-transfer interrupts */
    hdma_tx.Instance = DMA1_Stream0;
    hdma_tx.Init.Request = DMA_REQUEST_SAI1_A;
    hdma_tx.Init.Direction = DMA_MEMORY_TO_PERIPH;
    hdma_tx.Init.PeriphInc = DMA_PINC_DISABLE;
    hdma_tx.Init.MemInc = DMA_MINC_ENABLE;
    hdma_tx.Init.PeriphDataAlignment = DMA_PDATAALIGN_HALFWORD;
    hdma_tx.Init.MemDataAlignment = DMA_MDATAALIGN_HALFWORD;
    hdma_tx.Init.Mode = DMA_CIRCULAR;
    hdma_tx.Init.Priority = DMA_PRIORITY_HIGH;
    if (HAL_DMA_Init(&hdma_tx) != HAL_OK)
        return false;
    __HAL_LINKDMA(&hsai_tx, hdmatx, hdma_tx);

    hdma_rx.Instance = DMA1_Stream1;
    hdma_rx.Init = hdma_tx.Init;
    hdma_rx.Init.Request = DMA_REQUEST_SAI1_B;
    hdma_rx.Init.Direction = DMA_PERIPH_TO_MEMORY;
    if (HAL_DMA_Init(&hdma_rx) != HAL_OK)
        return false;
    __HAL_LINKDMA(&hsai_rx, hdmarx, hdma_rx);

    HAL_NVIC_SetPriority(DMA1_Stream0_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(DMA1_Stream0_IRQn);
    HAL_NVIC_SetPriority(DMA1_Stream1_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(DMA1_Stream1_IRQn);
    return true;
}

void sai_stream_start(void)
{
    memset(tx_buf, 0, sizeof(tx_buf));
    HAL_SAI_Receive_DMA(&hsai_rx, (uint8_t *)rx_buf, BUF_SAMPLES);
    HAL_SAI_Transmit_DMA(&hsai_tx, (uint8_t *)tx_buf, BUF_SAMPLES);
}

/* --- DMA progress: hand each completed 20 ms half to the application --- */
static void handle_half(int half)
{
    if (!frame_cb)
        return;
    const int16_t *rx = &rx_buf[half ? HALF_SAMPLES : 0];
    int16_t *tx = &tx_buf[half ? HALF_SAMPLES : 0];
    SCB_InvalidateDCache_by_Addr((uint32_t *)rx,
                                 HALF_SAMPLES * sizeof(int16_t));
    frame_cb(rx, tx);
    SCB_CleanDCache_by_Addr((uint32_t *)tx, HALF_SAMPLES * sizeof(int16_t));
}

void HAL_SAI_RxHalfCpltCallback(SAI_HandleTypeDef *h)
{
    if (h == &hsai_rx)
        handle_half(0);
}

void HAL_SAI_RxCpltCallback(SAI_HandleTypeDef *h)
{
    if (h == &hsai_rx)
        handle_half(1);
}

void DMA1_Stream0_IRQHandler(void) { HAL_DMA_IRQHandler(&hdma_tx); }
void DMA1_Stream1_IRQHandler(void) { HAL_DMA_IRQHandler(&hdma_rx); }
