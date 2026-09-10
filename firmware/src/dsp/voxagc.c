#include "voxagc.h"
#include <stdlib.h>

#define AGC_TARGET    8000      /* target peak envelope             */
#define AGC_MAX_Q8    (8 << 8)  /* max gain 8x                      */
#define AGC_MIN_Q8    (1 << 6)  /* min gain 0.25x                   */

void voxagc_init(voxagc_t *s)
{
    s->hp_x1 = s->hp_y1 = 0;
    s->env = 0;
    s->gain_q8 = 1 << 8;
    s->vox_env = 0;
    s->vox_hang = 0;
    s->vox_open = false;
}

/* first-order HPF, fc ~ 300 Hz @ 8 kHz: y = a*(y1 + x - x1), a ~ 0.79 */
static inline int16_t hpf(voxagc_t *s, int16_t x)
{
    int32_t y = (202 * (s->hp_y1 + x - s->hp_x1)) >> 8;
    s->hp_x1 = x;
    s->hp_y1 = y;
    if (y > 32767) y = 32767;
    if (y < -32768) y = -32768;
    return (int16_t)y;
}

static const int16_t db_env[] = {
    /* envelope thresholds for -40..-10 dBFS in 5 dB steps */
    327, 581, 1033, 1837, 3267, 5812, 10338
};

static int32_t thresh_from_db(int db)
{
    int idx = (db + 40) / 5;
    if (idx < 0) idx = 0;
    if (idx > 6) idx = 6;
    return db_env[idx];
}

bool voxagc_process(voxagc_t *s, int16_t *pcm, size_t n,
                    bool agc_enable, int vox_thresh_db, int vox_hang_frames)
{
    int32_t peak = 0;
    for (size_t i = 0; i < n; i++) {
        int16_t x = hpf(s, pcm[i]);
        if (agc_enable) {
            int32_t y = ((int32_t)x * s->gain_q8) >> 8;
            if (y > 32767) y = 32767;
            if (y < -32768) y = -32768;
            x = (int16_t)y;
        }
        pcm[i] = x;
        int32_t a = abs(x);
        if (a > peak)
            peak = a;
    }
    /* envelope: fast attack, slow decay */
    if (peak > s->env)
        s->env += (peak - s->env) >> 2;
    else
        s->env -= (s->env - peak) >> 6;

    if (agc_enable && s->env > 100) {
        int32_t want = (AGC_TARGET << 8) / s->env;
        if (want > AGC_MAX_Q8) want = AGC_MAX_Q8;
        if (want < AGC_MIN_Q8) want = AGC_MIN_Q8;
        /* slew gently */
        s->gain_q8 += (want - s->gain_q8) >> 5;
    }

    /* VOX on the (conditioned) envelope */
    if (s->env > thresh_from_db(vox_thresh_db)) {
        s->vox_open = true;
        s->vox_hang = (uint32_t)vox_hang_frames;
    } else if (s->vox_hang > 0) {
        s->vox_hang--;
    } else {
        s->vox_open = false;
    }
    return s->vox_open;
}
