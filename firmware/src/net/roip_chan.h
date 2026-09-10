/* Per-radio RoIP channel: RTP session, jitter buffer, PTT/COR logic. */
#ifndef ROIP_CHAN_H
#define ROIP_CHAN_H

#include <stdint.h>
#include <stdbool.h>
#include "lwip/ip_addr.h"
#include "../app_config.h"
#include "../ed137/rtp_ed137.h"

typedef struct {
    roip_channel_id_t id;
    /* session */
    bool session_up;
    ip_addr_t peer_ip;
    uint16_t peer_port;
    struct udp_pcb *pcb;
    rtp_state_t rtp;
    /* jitter buffer: ring of decoded PCM frames */
    int16_t jb[16][CFG_FRAME_SAMPLES];
    ed137_sig_t jb_sig[16];
    uint8_t jb_wr, jb_rd, jb_level, jb_target;
    bool jb_primed;
    /* radio-side state */
    bool cor_active;             /* squelch open (debounced)          */
    uint32_t cor_change_ms;
    bool ptt_keyed;              /* we are keying the radio           */
    uint32_t ptt_since_ms;
    uint32_t last_tx_ms;         /* last RTP packet sent              */
    uint32_t last_rx_ms;         /* last RTP packet received          */
    ed137_sig_t rx_sig;          /* latest signalling from network    */
} roip_chan_t;

void roip_chan_init(roip_chan_t *ch, roip_channel_id_t id,
                    uint16_t local_port);
void roip_chan_set_peer(roip_chan_t *ch, const ip_addr_t *ip, uint16_t port);
void roip_chan_session(roip_chan_t *ch, bool up);

/* called from the audio interrupt every 20 ms with this channel's
 * captured PCM; fills play with the next frame to send to the radio. */
void roip_chan_audio_frame(roip_chan_t *ch, const int16_t *cap,
                           int16_t *play, uint32_t now_ms);

/* housekeeping from the main loop: COR debounce, PTT guard, keepalives */
void roip_chan_poll(roip_chan_t *ch, uint32_t now_ms);

#endif
