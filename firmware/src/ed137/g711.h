/* G.711 mu-law codec (PCMU) */
#ifndef G711_H
#define G711_H

#include <stdint.h>
#include <stddef.h>

uint8_t g711_ulaw_encode(int16_t pcm);
int16_t g711_ulaw_decode(uint8_t ulaw);

void g711_encode_buf(const int16_t *pcm, uint8_t *out, size_t n);
void g711_decode_buf(const uint8_t *in, int16_t *pcm, size_t n);

#endif
