/* ATC RoIP Gateway - application configuration (compile-time defaults;
 * most values are also adjustable at runtime over the UART console). */
#ifndef APP_CONFIG_H
#define APP_CONFIG_H

#include <stdint.h>
#include <stdbool.h>

/* ---- Network ------------------------------------------------------------ */
#define CFG_USE_DHCP          1
#define CFG_STATIC_IP         "192.168.1.80"     /* used when DHCP off      */
#define CFG_STATIC_MASK       "255.255.255.0"
#define CFG_STATIC_GW         "192.168.1.1"

/* ---- Session mode -------------------------------------------------------
 * SIP mode: the gateway is an ED-137-style radio endpoint; the ground VCS /
 * remote operator INVITEs each channel URI (vhf@<ip>, hf@<ip>).
 * STATIC mode: no signalling, RTP flows to/from a fixed peer (bring-up). */
#define CFG_SIP_ENABLE        1
#define CFG_SIP_PORT          5060
#define CFG_STATIC_PEER_IP    "192.168.1.10"
#define CFG_RTP_PORT_VHF      5004               /* local RTP ports         */
#define CFG_RTP_PORT_HF       5006
#define CFG_STATIC_PEER_PORT_VHF 5004
#define CFG_STATIC_PEER_PORT_HF  5006

/* ---- Audio / RTP -------------------------------------------------------- */
#define CFG_SAMPLE_RATE       8000               /* ED-137 radio: 8 kHz     */
#define CFG_FRAME_MS          20                 /* RTP packet duration     */
#define CFG_FRAME_SAMPLES     (CFG_SAMPLE_RATE * CFG_FRAME_MS / 1000)
#define CFG_PAYLOAD_TYPE      0                  /* PCMU (G.711 u-law)      */
#define CFG_JITTER_MIN_MS     40
#define CFG_JITTER_MAX_MS     120
#define CFG_R2S_PERIOD_MS     200                /* keepalive when idle     */

/* ---- PTT / COR behaviour ------------------------------------------------ */
#define CFG_PTT_MAX_MS        120000             /* stuck-PTT guard (2 min) */
#define CFG_COR_DEBOUNCE_MS   20
#define CFG_HF_TUNE_DELAY_MS  50    /* PTT->audio delay for HF coupler keying */

/* ---- VOX (used when a radio has no COR line wired) ---------------------- */
#define CFG_VOX_ENABLE_VHF    0
#define CFG_VOX_ENABLE_HF     0
#define CFG_VOX_THRESH_DB     -30
#define CFG_VOX_HANG_MS       350

typedef enum { CH_VHF = 0, CH_HF = 1, CH_COUNT = 2 } roip_channel_id_t;

#endif /* APP_CONFIG_H */
