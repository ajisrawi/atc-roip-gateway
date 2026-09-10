#include "roip_chan.h"
#include "../board.h"
#include "../ed137/g711.h"
#include "lwip/udp.h"
#include <string.h>

static void set_ptt_gpio(roip_channel_id_t id, bool key)
{
    if (id == CH_VHF)
        HAL_GPIO_WritePin(PTT_VHF_PORT, PTT_VHF_PIN,
                          key ? GPIO_PIN_SET : GPIO_PIN_RESET);
    else
        HAL_GPIO_WritePin(PTT_HF_PORT, PTT_HF_PIN,
                          key ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static bool read_cor_gpio(roip_channel_id_t id)
{
    /* opto pulls the line LOW when the radio squelch is open */
    GPIO_PinState s = (id == CH_VHF)
        ? HAL_GPIO_ReadPin(COR_VHF_PORT, COR_VHF_PIN)
        : HAL_GPIO_ReadPin(COR_HF_PORT, COR_HF_PIN);
    return s == GPIO_PIN_RESET;
}

/* ---------------- network receive ---------------------------------------- */
static void on_rtp(void *arg, struct udp_pcb *pcb, struct pbuf *p,
                   const ip_addr_t *addr, u16_t port)
{
    (void)pcb; (void)addr; (void)port;
    roip_chan_t *ch = arg;
    uint8_t buf[512];
    size_t len = p->tot_len < sizeof(buf) ? p->tot_len : sizeof(buf);
    pbuf_copy_partial(p, buf, (u16_t)len, 0);
    pbuf_free(p);

    ed137_sig_t sig;
    const uint8_t *payload;
    size_t plen;
    uint16_t seq;
    uint32_t ts;
    if (!rtp_ed137_parse(buf, len, &sig, &payload, &plen, &seq, &ts))
        return;
    ch->rx_sig = sig;
    ch->last_rx_ms = HAL_GetTick();

    if (plen >= CFG_FRAME_SAMPLES) {
        uint8_t next = (uint8_t)((ch->jb_wr + 1) % 16);
        if (next != ch->jb_rd) {          /* drop when full */
            g711_decode_buf(payload, ch->jb[ch->jb_wr], CFG_FRAME_SAMPLES);
            ch->jb_sig[ch->jb_wr] = sig;
            ch->jb_wr = next;
            if (ch->jb_level < 15)
                ch->jb_level++;
        }
    }
}

void roip_chan_init(roip_chan_t *ch, roip_channel_id_t id,
                    uint16_t local_port)
{
    memset(ch, 0, sizeof(*ch));
    ch->id = id;
    ch->jb_target = (uint8_t)(CFG_JITTER_MIN_MS / CFG_FRAME_MS);
    rtp_init(&ch->rtp, 0x524F4950u + id, CFG_PAYLOAD_TYPE);
    ch->pcb = udp_new();
    udp_bind(ch->pcb, IP_ADDR_ANY, local_port);
    udp_recv(ch->pcb, on_rtp, ch);
}

void roip_chan_set_peer(roip_chan_t *ch, const ip_addr_t *ip, uint16_t port)
{
    ch->peer_ip = *ip;
    ch->peer_port = port;
}

void roip_chan_session(roip_chan_t *ch, bool up)
{
    ch->session_up = up;
    if (!up) {
        ch->ptt_keyed = false;
        set_ptt_gpio(ch->id, false);
        ch->jb_rd = ch->jb_wr = ch->jb_level = 0;
        ch->jb_primed = false;
    }
}

static void send_rtp(roip_chan_t *ch, const uint8_t *payload, size_t plen,
                     bool marker, uint32_t now_ms)
{
    ed137_sig_t sig = {
        .ptt_type = ED137_PTT_OFF,   /* we are the radio side: PTT echoes
                                        what the operator keys, not us    */
        .ptt_id = ch->id,
        .squ = ch->cor_active,
        .sct = false,
    };
    uint8_t pkt[32 + CFG_FRAME_SAMPLES];
    size_t n = rtp_ed137_build(&ch->rtp, &sig, payload, plen, marker, pkt);
    struct pbuf *p = pbuf_alloc(PBUF_TRANSPORT, (u16_t)n, PBUF_RAM);
    if (!p)
        return;
    memcpy(p->payload, pkt, n);
    udp_sendto(ch->pcb, p, &ch->peer_ip, ch->peer_port);
    pbuf_free(p);
    ch->last_tx_ms = now_ms;
}

void roip_chan_audio_frame(roip_chan_t *ch, const int16_t *cap,
                           int16_t *play, uint32_t now_ms)
{
    /* ---- uplink: radio RX audio -> network (while squelch open) ---- */
    if (ch->session_up && ch->cor_active) {
        uint8_t ulaw[CFG_FRAME_SAMPLES];
        g711_encode_buf(cap, ulaw, CFG_FRAME_SAMPLES);
        send_rtp(ch, ulaw, sizeof(ulaw), false, now_ms);
    }

    /* ---- downlink: jitter buffer -> radio (keyed by remote PTT) ---- */
    bool want_ptt = ch->session_up &&
                    ch->rx_sig.ptt_type != ED137_PTT_OFF &&
                    (now_ms - ch->last_rx_ms) < 500;
    if (want_ptt && !ch->ptt_keyed) {
        ch->ptt_keyed = true;
        ch->ptt_since_ms = now_ms;
        set_ptt_gpio(ch->id, true);
    } else if (!want_ptt && ch->ptt_keyed) {
        ch->ptt_keyed = false;
        set_ptt_gpio(ch->id, false);
    }

    if (!ch->jb_primed && ch->jb_level >= ch->jb_target)
        ch->jb_primed = true;
    if (ch->jb_primed && ch->jb_rd != ch->jb_wr) {
        memcpy(play, ch->jb[ch->jb_rd],
               CFG_FRAME_SAMPLES * sizeof(int16_t));
        ch->jb_rd = (uint8_t)((ch->jb_rd + 1) % 16);
        if (ch->jb_level)
            ch->jb_level--;
        if (ch->jb_rd == ch->jb_wr)
            ch->jb_primed = false;        /* ran dry: re-prime */
    } else {
        memset(play, 0, CFG_FRAME_SAMPLES * sizeof(int16_t));
    }
}

void roip_chan_poll(roip_chan_t *ch, uint32_t now_ms)
{
    /* COR debounce */
    bool raw = read_cor_gpio(ch->id);
    if (raw != ch->cor_active &&
            (now_ms - ch->cor_change_ms) > CFG_COR_DEBOUNCE_MS) {
        ch->cor_active = raw;
        ch->cor_change_ms = now_ms;
    }
    /* stuck-PTT guard */
    if (ch->ptt_keyed && (now_ms - ch->ptt_since_ms) > CFG_PTT_MAX_MS) {
        ch->ptt_keyed = false;
        set_ptt_gpio(ch->id, false);
    }
    /* R2S-style keepalive while the session is idle */
    if (ch->session_up &&
            (now_ms - ch->last_tx_ms) >= CFG_R2S_PERIOD_MS) {
        send_rtp(ch, NULL, 0, false, now_ms);
    }
}
