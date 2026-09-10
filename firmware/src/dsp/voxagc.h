/* Per-channel audio conditioning: DC-blocking HPF, simple AGC, VOX. */
#ifndef VOXAGC_H
#define VOXAGC_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

typedef struct {
    /* DC-block / 300 Hz HPF state */
    int32_t hp_x1, hp_y1;
    /* AGC */
    int32_t env;             /* envelope (Q16)     */
    int32_t gain_q8;         /* current gain, Q8   */
    /* VOX */
    int32_t vox_env;
    uint32_t vox_hang;       /* frames remaining   */
    bool vox_open;
} voxagc_t;

void voxagc_init(voxagc_t *s);

/* process n samples in place; returns true if VOX considers speech present */
bool voxagc_process(voxagc_t *s, int16_t *pcm, size_t n,
                    bool agc_enable, int vox_thresh_db, int vox_hang_frames);

#endif
