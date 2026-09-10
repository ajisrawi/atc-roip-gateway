#include "sip_mini.h"
#include "lwip/udp.h"
#include "lwip/netif.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static struct udp_pcb *sip_pcb;
static sip_session_cb session_cb;
static sip_dialog_t dialogs[CH_COUNT];
static uint32_t tag_seed = 0x51900001;

static const char *chan_user(roip_channel_id_t ch)
{
    return ch == CH_VHF ? "vhf" : "hf";
}

static uint16_t chan_rtp_port(roip_channel_id_t ch)
{
    return ch == CH_VHF ? CFG_RTP_PORT_VHF : CFG_RTP_PORT_HF;
}

/* ---------------- tiny SIP message parsing ------------------------------- */
typedef struct {
    char method[16];
    char via[256], from[256], to[256], call_id[128], cseq[64];
    char contact[128];
    const char *body;
    int content_length;
} sip_msg_t;

static bool header_get(const char *msg, const char *name, const char *alias,
                       char *out, size_t outsz)
{
    const char *p = msg;
    size_t nlen = strlen(name);
    size_t alen = alias ? strlen(alias) : 0;
    while ((p = strstr(p, "\r\n")) != NULL) {
        p += 2;
        if (!strncasecmp(p, name, nlen) && p[nlen] == ':') {
            p += nlen + 1;
        } else if (alias && !strncasecmp(p, alias, alen) && p[alen] == ':') {
            p += alen + 1;
        } else {
            continue;
        }
        while (*p == ' ')
            p++;
        const char *e = strstr(p, "\r\n");
        if (!e)
            return false;
        size_t n = (size_t)(e - p);
        if (n >= outsz)
            n = outsz - 1;
        memcpy(out, p, n);
        out[n] = 0;
        return true;
    }
    return false;
}

static bool sip_parse(const char *raw, size_t len, sip_msg_t *m)
{
    (void)len;
    memset(m, 0, sizeof(*m));
    const char *sp = strchr(raw, ' ');
    if (!sp || (size_t)(sp - raw) >= sizeof(m->method))
        return false;
    memcpy(m->method, raw, (size_t)(sp - raw));
    header_get(raw, "Via", "v", m->via, sizeof(m->via));
    header_get(raw, "From", "f", m->from, sizeof(m->from));
    header_get(raw, "To", "t", m->to, sizeof(m->to));
    header_get(raw, "Call-ID", "i", m->call_id, sizeof(m->call_id));
    header_get(raw, "CSeq", NULL, m->cseq, sizeof(m->cseq));
    header_get(raw, "Contact", "m", m->contact, sizeof(m->contact));
    char cl[16];
    if (header_get(raw, "Content-Length", "l", cl, sizeof(cl)))
        m->content_length = atoi(cl);
    const char *b = strstr(raw, "\r\n\r\n");
    m->body = b ? b + 4 : NULL;
    return true;
}

/* extract "c=" address and audio "m=" port from an SDP offer */
static bool sdp_peer(const char *sdp, ip_addr_t *ip, uint16_t *port)
{
    if (!sdp)
        return false;
    const char *c = strstr(sdp, "c=IN IP4 ");
    const char *m = strstr(sdp, "m=audio ");
    if (!c || !m)
        return false;
    char addr[32] = {0};
    sscanf(c + 9, "%31[0-9.]", addr);
    unsigned p = 0;
    sscanf(m + 8, "%u", &p);
    if (!ipaddr_aton(addr, ip) || p == 0)
        return false;
    *port = (uint16_t)p;
    return true;
}

static void send_response(const ip_addr_t *dst, uint16_t dport,
                          const sip_msg_t *req, int code, const char *reason,
                          const char *to_tag, const char *extra_hdrs,
                          const char *body, const char *ctype)
{
    char to[300];
    if (to_tag && !strstr(req->to, ";tag="))
        snprintf(to, sizeof(to), "%s;tag=%s", req->to, to_tag);
    else
        snprintf(to, sizeof(to), "%s", req->to);
    char msg[1200];
    int blen = body ? (int)strlen(body) : 0;
    int n = snprintf(msg, sizeof(msg),
        "SIP/2.0 %d %s\r\n"
        "Via: %s\r\n"
        "From: %s\r\n"
        "To: %s\r\n"
        "Call-ID: %s\r\n"
        "CSeq: %s\r\n"
        "Allow: INVITE, ACK, BYE, CANCEL, OPTIONS\r\n"
        "%s"
        "Content-Length: %d\r\n"
        "%s%s"
        "\r\n%s",
        code, reason, req->via, req->from, to, req->call_id, req->cseq,
        extra_hdrs ? extra_hdrs : "", blen,
        ctype ? "Content-Type: " : "", ctype ? ctype : "",
        body ? body : "");
    if (n <= 0 || n >= (int)sizeof(msg))
        return;
    struct pbuf *p = pbuf_alloc(PBUF_TRANSPORT, (u16_t)n, PBUF_RAM);
    if (!p)
        return;
    memcpy(p->payload, msg, (size_t)n);
    udp_sendto(sip_pcb, p, dst, dport);
    pbuf_free(p);
}

/* WG67/ED-137 flavoured SDP answer for one radio channel */
static void make_sdp(roip_channel_id_t ch, char *out, size_t sz)
{
    const ip4_addr_t *ip = netif_ip4_addr(netif_default);
    char a[20];
    ip4addr_ntoa_r(ip, a, sizeof(a));
    snprintf(out, sz,
        "v=0\r\n"
        "o=roipgw 0 0 IN IP4 %s\r\n"
        "s=radio\r\n"
        "c=IN IP4 %s\r\n"
        "t=0 0\r\n"
        "m=audio %u RTP/AVP %u\r\n"
        "a=rtpmap:%u PCMU/8000\r\n"
        "a=ptime:%u\r\n"
        "a=type:radio\r\n"          /* WG67 media attribute            */
        "a=txrxmode:TxRx\r\n"       /* transceiver (tx and rx capable) */
        "a=R2S-KeepAlivePeriod:%u\r\n",
        a, a, chan_rtp_port(ch), CFG_PAYLOAD_TYPE, CFG_PAYLOAD_TYPE,
        CFG_FRAME_MS, CFG_R2S_PERIOD_MS);
}

static roip_channel_id_t channel_for_request(const char *raw)
{
    /* request-URI is on the first line: INVITE sip:vhf@host SIP/2.0 */
    char line[128] = {0};
    const char *e = strstr(raw, "\r\n");
    size_t n = e ? (size_t)(e - raw) : sizeof(line) - 1;
    if (n >= sizeof(line))
        n = sizeof(line) - 1;
    memcpy(line, raw, n);
    if (strstr(line, "sip:hf@") || strstr(line, "sip:hf%40"))
        return CH_HF;
    return CH_VHF;
}

static void on_udp(void *arg, struct udp_pcb *pcb, struct pbuf *p,
                   const ip_addr_t *addr, u16_t port)
{
    (void)arg; (void)pcb;
    char raw[1500];
    size_t len = p->tot_len < sizeof(raw) - 1 ? p->tot_len : sizeof(raw) - 1;
    pbuf_copy_partial(p, raw, (u16_t)len, 0);
    raw[len] = 0;
    pbuf_free(p);

    sip_msg_t m;
    if (!sip_parse(raw, len, &m))
        return;
    roip_channel_id_t ch = channel_for_request(raw);
    sip_dialog_t *d = &dialogs[ch];

    if (!strcmp(m.method, "OPTIONS")) {
        send_response(addr, port, &m, 200, "OK", NULL, NULL, NULL, NULL);
    } else if (!strcmp(m.method, "INVITE")) {
        ip_addr_t peer;
        uint16_t rtp_port;
        if (!sdp_peer(m.body, &peer, &rtp_port)) {
            send_response(addr, port, &m, 488, "Not Acceptable Here",
                          NULL, NULL, NULL, NULL);
            return;
        }
        snprintf(d->to_tag, sizeof(d->to_tag), "%08lx",
                 (unsigned long)tag_seed++);
        snprintf(d->call_id, sizeof(d->call_id), "%s", m.call_id);
        d->peer_ip = peer;
        d->peer_rtp_port = rtp_port;
        char sdp[512];
        make_sdp(ch, sdp, sizeof(sdp));
        send_response(addr, port, &m, 200, "OK", d->to_tag, NULL,
                      sdp, "application/sdp\r\n");
        /* session considered up on ACK; be tolerant and arm now */
        d->active = true;
        if (session_cb)
            session_cb(ch, true, &d->peer_ip, d->peer_rtp_port);
    } else if (!strcmp(m.method, "ACK")) {
        /* nothing further: already armed on 200 */
    } else if (!strcmp(m.method, "BYE") || !strcmp(m.method, "CANCEL")) {
        send_response(addr, port, &m, 200, "OK", NULL, NULL, NULL, NULL);
        if (d->active && !strcmp(d->call_id, m.call_id)) {
            d->active = false;
            if (session_cb)
                session_cb(ch, false, NULL, 0);
        }
    } else {
        send_response(addr, port, &m, 501, "Not Implemented",
                      NULL, NULL, NULL, NULL);
    }
}

void sip_init(sip_session_cb cb)
{
    session_cb = cb;
    memset(dialogs, 0, sizeof(dialogs));
    sip_pcb = udp_new();
    udp_bind(sip_pcb, IP_ADDR_ANY, CFG_SIP_PORT);
    udp_recv(sip_pcb, on_udp, NULL);
}

void sip_poll(uint32_t now_ms)
{
    (void)now_ms;   /* dialog timers / re-INVITE handling: future work */
}

const sip_dialog_t *sip_dialog(roip_channel_id_t ch)
{
    return &dialogs[ch];
}
