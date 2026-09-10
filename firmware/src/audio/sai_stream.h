/* SAI1 full-duplex stereo streaming with DMA double buffering.
 *
 * Block A = master TX (to codec DIN), Block B = synchronous slave RX
 * (from codec DOUT).  Interleaved L/R 16-bit frames; L = VHF, R = HF.
 * Each half-buffer holds CFG_FRAME_SAMPLES stereo frames (20 ms).
 */
#ifndef SAI_STREAM_H
#define SAI_STREAM_H

#include <stdint.h>
#include <stdbool.h>
#include "../app_config.h"

/* callback runs in interrupt context when 20 ms of audio is ready;
 * rx points at CFG_FRAME_SAMPLES*2 interleaved samples just captured,
 * tx points at the buffer to fill for the next 20 ms of playback. */
typedef void (*sai_frame_cb)(const int16_t *rx, int16_t *tx);

bool sai_stream_init(sai_frame_cb cb);
void sai_stream_start(void);

#endif
