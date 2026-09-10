/* RTP with the ED-137 Radio-profile header extension.
 *
 * The ED-137B/C Radio profile carries PTT and squelch signalling in an RTP
 * header extension (RFC 3550 mechanism).  The extension "defined by profile"
 * id and the bit layout of the signalling word are defined by EUROCAE
 * ED-137; the constants below follow the widely used layout (cf. the
 * Wireshark ED-137 dissector) and are grouped here so they can be verified
 * against the licensed standard text in ONE place.
 */
#ifndef RTP_ED137_H
#define RTP_ED137_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* extension profile identifiers */
#define ED137_EXT_PROFILE     0x0067u    /* ED-137B signalling extension  */
#define ED137A_EXT_PROFILE    0x0167u    /* legacy ED-137A                */

/* PTT type field values */
typedef enum {
    ED137_PTT_OFF       = 0,
    ED137_PTT_NORMAL    = 1,
    ED137_PTT_COUPLING  = 2,
    ED137_PTT_PRIORITY  = 3,
    ED137_PTT_EMERGENCY = 4,
} ed137_ptt_t;

typedef struct {
    ed137_ptt_t ptt_type;    /* transmit keying state              */
    uint8_t     ptt_id;      /* transmitter id, 4 bits             */
    bool        squ;         /* squelch open (receive carrier)     */
    bool        sct;         /* simultaneous call transmission     */
} ed137_sig_t;

typedef struct {
    uint16_t seq;
    uint32_t timestamp;
    uint32_t ssrc;
    uint8_t  payload_type;
} rtp_state_t;

void rtp_init(rtp_state_t *st, uint32_t ssrc, uint8_t payload_type);

/* Build an RTP packet with the ED-137 extension.
 * payload may be NULL/len 0 for a signalling-only (R2S keepalive) packet.
 * Returns total packet length written to buf (buf must fit 16 + 4 + len). */
size_t rtp_ed137_build(rtp_state_t *st, const ed137_sig_t *sig,
                       const uint8_t *payload, size_t len,
                       bool marker, uint8_t *buf);

/* Parse an incoming packet.  Returns payload pointer/len via out params and
 * fills sig (defaults: PTT_OFF/!squ when no extension present).
 * Returns false if the packet is not valid RTP. */
bool rtp_ed137_parse(const uint8_t *buf, size_t len,
                     ed137_sig_t *sig, const uint8_t **payload,
                     size_t *payload_len, uint16_t *seq, uint32_t *ts);

#endif /* RTP_ED137_H */
