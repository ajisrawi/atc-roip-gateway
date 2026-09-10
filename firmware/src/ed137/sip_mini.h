/* Minimal SIP UAS for the ED-137 radio endpoint role.
 *
 * Supports: OPTIONS, INVITE (with SDP answer), ACK, BYE, CANCEL.
 * One dialog per radio channel (URIs vhf@<host> and hf@<host>).
 * Transport: UDP only.  This is deliberately small: enough for a VCS or
 * softphone-style operator position to bring a session up and down.
 */
#ifndef SIP_MINI_H
#define SIP_MINI_H

#include <stdint.h>
#include <stdbool.h>
#include "lwip/ip_addr.h"
#include "../app_config.h"

typedef struct {
    bool      active;              /* dialog established           */
    ip_addr_t peer_ip;             /* negotiated RTP destination   */
    uint16_t  peer_rtp_port;
    char      call_id[64];
    char      from_tag[32];
    char      to_tag[16];
} sip_dialog_t;

typedef void (*sip_session_cb)(roip_channel_id_t ch, bool up,
                               const ip_addr_t *peer, uint16_t rtp_port);

void sip_init(sip_session_cb cb);
void sip_poll(uint32_t now_ms);
const sip_dialog_t *sip_dialog(roip_channel_id_t ch);

#endif
