#include "rtp_ed137.h"
#include <string.h>

#define RTP_VERSION 2u

static void put16(uint8_t *p, uint16_t v) { p[0] = v >> 8; p[1] = v & 0xFF; }
static void put32(uint8_t *p, uint32_t v)
{
    p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v & 0xFF;
}
static uint16_t get16(const uint8_t *p) { return (p[0] << 8) | p[1]; }
static uint32_t get32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | p[3];
}

void rtp_init(rtp_state_t *st, uint32_t ssrc, uint8_t payload_type)
{
    st->seq = 0;
    st->timestamp = 0;
    st->ssrc = ssrc;
    st->payload_type = payload_type;
}

/* ED-137 signalling word (32 bit, one extension word):
 *   [31:29] PTT type    [28] SQU    [27:24] PTT-id
 *   [23]    SCT         [22:1] reserved / feature bits   [0] X (more ext)
 */
static uint32_t sig_word(const ed137_sig_t *s)
{
    uint32_t w = 0;
    w |= ((uint32_t)(s->ptt_type & 0x7)) << 29;
    w |= ((uint32_t)(s->squ ? 1 : 0)) << 28;
    w |= ((uint32_t)(s->ptt_id & 0xF)) << 24;
    w |= ((uint32_t)(s->sct ? 1 : 0)) << 23;
    return w;
}

static void sig_unpack(uint32_t w, ed137_sig_t *s)
{
    s->ptt_type = (ed137_ptt_t)((w >> 29) & 0x7);
    s->squ      = (w >> 28) & 1;
    s->ptt_id   = (w >> 24) & 0xF;
    s->sct      = (w >> 23) & 1;
}

size_t rtp_ed137_build(rtp_state_t *st, const ed137_sig_t *sig,
                       const uint8_t *payload, size_t len,
                       bool marker, uint8_t *buf)
{
    uint8_t *p = buf;
    /* V=2, P=0, X=1 (extension always present), CC=0 */
    p[0] = (RTP_VERSION << 6) | (1u << 4);
    p[1] = (marker ? 0x80 : 0x00) | (st->payload_type & 0x7F);
    put16(p + 2, st->seq);
    put32(p + 4, st->timestamp);
    put32(p + 8, st->ssrc);
    p += 12;
    /* extension header: profile id + length (in 32-bit words) */
    put16(p, ED137_EXT_PROFILE);
    put16(p + 2, 1);
    put32(p + 4, sig_word(sig));
    p += 8;
    if (payload && len) {
        memcpy(p, payload, len);
        p += len;
        st->timestamp += (uint32_t)len;   /* PCMU: 1 sample per byte */
    }
    st->seq++;
    return (size_t)(p - buf);
}

bool rtp_ed137_parse(const uint8_t *buf, size_t len,
                     ed137_sig_t *sig, const uint8_t **payload,
                     size_t *payload_len, uint16_t *seq, uint32_t *ts)
{
    if (len < 12)
        return false;
    uint8_t v = buf[0] >> 6;
    if (v != RTP_VERSION)
        return false;
    bool x = (buf[0] >> 4) & 1;
    uint8_t cc = buf[0] & 0x0F;
    *seq = get16(buf + 2);
    *ts = get32(buf + 4);
    size_t off = 12 + 4u * cc;
    memset(sig, 0, sizeof(*sig));
    if (x) {
        if (len < off + 4)
            return false;
        uint16_t profile = get16(buf + off);
        uint16_t words = get16(buf + off + 2);
        if (len < off + 4 + 4u * words)
            return false;
        if ((profile == ED137_EXT_PROFILE || profile == ED137A_EXT_PROFILE)
                && words >= 1)
            sig_unpack(get32(buf + off + 4), sig);
        off += 4 + 4u * words;
    }
    uint8_t pad = (buf[0] >> 5) & 1 ? buf[len - 1] : 0;
    if (off + pad > len)
        return false;
    *payload = buf + off;
    *payload_len = len - off - pad;
    return true;
}
