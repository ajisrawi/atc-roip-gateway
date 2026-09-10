#include "g711.h"

#define BIAS 0x84
#define CLIP 32635

uint8_t g711_ulaw_encode(int16_t pcm)
{
    int sign = (pcm >> 8) & 0x80;
    if (sign)
        pcm = (int16_t)-pcm;
    if (pcm > CLIP)
        pcm = CLIP;
    pcm = (int16_t)(pcm + BIAS);
    int exponent = 7;
    for (int mask = 0x4000; (pcm & mask) == 0 && exponent > 0; mask >>= 1)
        exponent--;
    int mantissa = (pcm >> (exponent + 3)) & 0x0F;
    return (uint8_t)~(sign | (exponent << 4) | mantissa);
}

int16_t g711_ulaw_decode(uint8_t ulaw)
{
    ulaw = (uint8_t)~ulaw;
    int sign = ulaw & 0x80;
    int exponent = (ulaw >> 4) & 0x07;
    int mantissa = ulaw & 0x0F;
    int sample = ((mantissa << 3) + BIAS) << exponent;
    sample -= BIAS;
    return (int16_t)(sign ? -sample : sample);
}

void g711_encode_buf(const int16_t *pcm, uint8_t *out, size_t n)
{
    while (n--)
        *out++ = g711_ulaw_encode(*pcm++);
}

void g711_decode_buf(const uint8_t *in, int16_t *pcm, size_t n)
{
    while (n--)
        *pcm++ = g711_ulaw_decode(*in++);
}
