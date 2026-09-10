"""Build the ATC RoIP Gateway design document PDF (styled, with diagrams)."""
import os
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, Table, TableStyle,
                                PageBreak, NextPageTemplate, KeepTogether,
                                Image)
from reportlab.graphics.shapes import (Drawing, Rect, String, Line, Polygon,
                                       Circle)
from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HW = os.path.join(ROOT, "hardware", "atc-roip-gateway")
BODY_PDF = os.path.join(HW, "_design-doc-body.pdf")
SCH_PDF = os.path.join(HW, "atc-roip-gateway-schematic.pdf")
OUT_PDF = os.path.join(ROOT, "ATC-RoIP-Gateway-Design-Document.pdf")

# ---------------------------------------------------------------- palette
NAVY = HexColor("#16324F")
BLUE = HexColor("#2F6DB3")
SKY = HexColor("#D9E6F2")
SLATE = HexColor("#5B6B7A")
LIGHT = HexColor("#EEF3F8")
LINE = HexColor("#C3D0DC")
AMBER = HexColor("#C8871E")
AMBER_L = HexColor("#F7EBD4")
GREEN = HexColor("#2E7D4F")
GREEN_L = HexColor("#DFEEE5")
INK = HexColor("#1C242C")
GRAY = HexColor("#8A97A3")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
USABLE = PAGE_W - 2 * MARGIN   # ~493 pt

DOC_TITLE = "ATC Radio-over-IP Gateway — Design Document"

# ---------------------------------------------------------------- styles
def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.5, leading=13.5,
                textColor=INK, spaceAfter=5, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)

st_h1 = S("h1", fontName="Helvetica-Bold", fontSize=16, leading=20,
          textColor=NAVY, spaceBefore=14, spaceAfter=6)
st_h2 = S("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15,
          textColor=BLUE, spaceBefore=10, spaceAfter=4)
st_body = S("body")
st_bullet = S("bullet", leftIndent=10, bulletIndent=2, spaceAfter=3)
st_caption = S("caption", fontSize=8, textColor=SLATE, alignment=TA_CENTER,
               spaceBefore=2, spaceAfter=10)
st_small = S("small", fontSize=8, leading=11, textColor=SLATE)
st_mono = S("mono", fontName="Courier", fontSize=8.5, leading=11.5,
            textColor=NAVY)
st_th = S("th", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
          textColor=white, spaceAfter=0)
st_td = S("td", fontSize=8.5, leading=11, spaceAfter=0)
st_td_b = S("td_b", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
            textColor=NAVY, spaceAfter=0)


def tbl(headers, rows, widths, aligns=None):
    data = [[Paragraph(h, st_th) for h in headers]]
    for r in rows:
        row = []
        for i, cell in enumerate(r):
            sty = st_td_b if i == 0 else st_td
            row.append(Paragraph(cell, sty))
        data.append(row)
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ---------------------------------------------------------------- diagrams
def box(d, x, y, w, h, title, sub=None, fill=LIGHT, stroke=BLUE,
        tcolor=NAVY, fs=8.5, sub_fs=6.5, rx=4):
    d.add(Rect(x, y, w, h, rx=rx, ry=rx, fillColor=fill, strokeColor=stroke,
               strokeWidth=1.1))
    cy = y + h / 2 + (3 if sub else -fs * 0.36)
    if sub:
        d.add(String(x + w / 2, cy, title, fontName="Helvetica-Bold",
                     fontSize=fs, fillColor=tcolor, textAnchor="middle"))
        lines = sub if isinstance(sub, list) else [sub]
        yy = cy - 9
        for ln in lines:
            d.add(String(x + w / 2, yy, ln, fontName="Helvetica",
                         fontSize=sub_fs, fillColor=SLATE,
                         textAnchor="middle"))
            yy -= 8
    else:
        d.add(String(x + w / 2, cy, title, fontName="Helvetica-Bold",
                     fontSize=fs, fillColor=tcolor, textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, color=SLATE, both=False, width=1.2, label=None,
          label_dy=5, lfs=6.5):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width))
    import math
    ang = math.atan2(y2 - y1, x2 - x1)

    def head(px, py, a):
        s = 5
        d.add(Polygon(points=[px, py,
                              px - s * math.cos(a - 0.42),
                              py - s * math.sin(a - 0.42),
                              px - s * math.cos(a + 0.42),
                              py - s * math.sin(a + 0.42)],
                      fillColor=color, strokeColor=color, strokeWidth=0.5))

    head(x2, y2, ang)
    if both:
        head(x1, y1, ang + 3.14159)
    if label:
        d.add(String((x1 + x2) / 2, (y1 + y2) / 2 + label_dy, label,
                     fontName="Helvetica-Oblique", fontSize=lfs,
                     fillColor=color, textAnchor="middle"))


def diagram_system():
    """End-to-end chain: controller <-> IP <-> Starlink <-> gateway <-> radios."""
    W, H = 493, 168
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=white, strokeColor=None))
    y0, bh = 96, 44
    # ground side
    box(d, 4, y0, 78, bh, "ATC / Remote", ["controller or", "remote pilot"],
        fill=SKY, stroke=BLUE)
    box(d, 108, y0, 78, bh, "ATC IP network", ["VCS / ED-137", "ground side"],
        fill=SKY, stroke=BLUE)
    box(d, 212, y0, 70, bh, "Starlink", ["LEO satcom", "~25-60 ms"],
        fill=LIGHT, stroke=SLATE)
    box(d, 308, y0, 82, bh, "RoIP GATEWAY", ["this design", "on aircraft"],
        fill=GREEN_L, stroke=GREEN)
    # radios stacked
    box(d, 420, y0 + 26, 69, 30, "VHF COM", ["118-137 MHz AM"],
        fill=AMBER_L, stroke=AMBER)
    box(d, 420, y0 - 12, 69, 30, "HF XCVR", ["2-30 MHz SSB"],
        fill=AMBER_L, stroke=AMBER)
    yc = y0 + bh / 2
    arrow(d, 82, yc, 108, yc, both=True, label="SIP/RTP")
    arrow(d, 186, yc, 212, yc, both=True, label="IP")
    arrow(d, 282, yc, 308, yc, both=True, label="Ethernet")
    arrow(d, 390, yc + 8, 420, y0 + 41, both=True)
    arrow(d, 390, yc - 8, 420, y0 + 3, both=True)
    d.add(String(405, y0 + 52, "audio / PTT / COR", fontName="Helvetica-Oblique",
                 fontSize=6.5, fillColor=SLATE, textAnchor="middle"))
    # aircraft boundary
    d.add(Rect(300, 66, 193, 96, rx=6, ry=6, fillColor=None,
               strokeColor=GRAY, strokeWidth=0.8, strokeDashArray=[3, 2]))
    d.add(String(396, 56, "AIRCRAFT", fontName="Helvetica-Bold", fontSize=7,
                 fillColor=GRAY, textAnchor="middle"))
    # payload strip
    d.add(Rect(4, 8, 485, 30, rx=4, ry=4, fillColor=LIGHT, strokeColor=LINE,
               strokeWidth=0.7))
    d.add(String(12, 26, "Stream:", fontName="Helvetica-Bold", fontSize=7.5,
                 fillColor=NAVY))
    d.add(String(12, 14, "RTP/UDP · 20 ms frames · Opus 16 kbit/s or "
                 "G.711 µ-law (ED-137 Radio profile) · PTT + squelch in RTP "
                 "header extension · adaptive 40-120 ms jitter buffer",
                 fontName="Helvetica", fontSize=7.5, fillColor=SLATE))
    return d


def diagram_board():
    """Board-level block diagram matching the five schematic sheets."""
    W, H = 493, 258
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=white, strokeColor=None))
    # board outline
    d.add(Rect(96, 32, 300, 214, rx=8, ry=8, fillColor=None, strokeColor=NAVY,
               strokeWidth=1.4))
    d.add(String(246, 250, "ATC RoIP GATEWAY — PCB", fontName="Helvetica-Bold",
                 fontSize=8, fillColor=NAVY, textAnchor="middle"))
    # power chain (bottom strip inside board)
    box(d, 108, 42, 66, 34, "Input prot.", ["fuse · Schottky", "SMCJ33A TVS"],
        fill=LIGHT, stroke=SLATE)
    box(d, 186, 42, 62, 34, "LM2576HV", ["buck 28V→5V", "60 V rated"],
        fill=LIGHT, stroke=SLATE)
    box(d, 260, 42, 58, 34, "AMS1117", ["5V→3.3V LDO"],
        fill=LIGHT, stroke=SLATE)
    box(d, 330, 42, 56, 34, "Ferrite split", ["+3.3VA / GNDA"],
        fill=LIGHT, stroke=SLATE)
    arrow(d, 174, 59, 186, 59)
    arrow(d, 248, 59, 260, 59)
    arrow(d, 318, 59, 330, 59)
    # 28V connector
    box(d, 10, 42, 58, 34, "J1", ["28 V DC", "aircraft bus"], fill=SKY,
        stroke=BLUE)
    arrow(d, 68, 59, 108, 59, label="28 V")
    # MCU center
    box(d, 206, 132, 96, 74, "STM32H743VIT6",
        ["Cortex-M7 480 MHz", "lwIP · RTP · Opus/G.711",
         "SAI · RMII · I2C · GPIO"], fill=SKY, stroke=BLUE, fs=9)
    # PHY + RJ45
    box(d, 108, 150, 74, 44, "LAN8742A", ["RMII PHY", "50 MHz REF_CLK out"],
        fill=LIGHT, stroke=BLUE)
    box(d, 10, 150, 74, 44, "RJ45 MagJack", ["integrated", "magnetics"],
        fill=SKY, stroke=BLUE)
    arrow(d, 182, 172, 206, 172, both=True, label="RMII")
    arrow(d, 84, 172, 108, 172, both=True, label="MDI")
    # codec
    box(d, 318, 150, 70, 44, "TLV320AIC23B", ["stereo codec", "L=VHF  R=HF"],
        fill=LIGHT, stroke=BLUE)
    arrow(d, 302, 172, 318, 172, both=True, label="I2S/SAI")
    # radio IF zone
    d.add(Rect(404, 32, 84, 214, rx=6, ry=6, fillColor=AMBER_L,
               strokeColor=AMBER, strokeWidth=1))
    d.add(String(446, 236, "ISOLATION", fontName="Helvetica-Bold", fontSize=7,
                 fillColor=AMBER, textAnchor="middle"))
    d.add(String(446, 227, "BARRIER", fontName="Helvetica-Bold", fontSize=7,
                 fillColor=AMBER, textAnchor="middle"))
    box(d, 410, 178, 72, 40, "VHF channel", ["2× 600R xfmr", "PTT + COR opto"],
        fill=white, stroke=AMBER)
    box(d, 410, 118, 72, 40, "HF channel", ["2× 600R xfmr", "PTT + COR opto"],
        fill=white, stroke=AMBER)
    box(d, 410, 52, 72, 40, "J5  DB25", ["to VHF COM", "and HF XCVR"],
        fill=white, stroke=AMBER)
    arrow(d, 388, 182, 410, 194, both=True)
    arrow(d, 388, 162, 410, 140, both=True)
    d.add(Line(446, 118, 446, 92, strokeColor=AMBER, strokeWidth=1.1))
    d.add(Line(446, 178, 452, 168, strokeColor=AMBER, strokeWidth=0))
    arrow(d, 446, 118, 446, 92, color=AMBER)
    arrow(d, 452, 178, 452, 96, color=AMBER)
    # aux headers
    box(d, 108, 96, 74, 34, "SWD + UART", ["debug · console"], fill=LIGHT,
        stroke=SLATE)
    arrow(d, 182, 113, 218, 132)
    box(d, 206, 96, 96, 22, "3× status LED", fill=LIGHT, stroke=SLATE, fs=7.5)
    arrow(d, 254, 118, 254, 132)
    return d


def diagram_channel():
    """Detail of one isolated radio channel."""
    W, H = 493, 200
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=white, strokeColor=None))
    d.add(String(120, 188, "GATEWAY SIDE (codec / MCU)",
                 fontName="Helvetica-Bold", fontSize=7.5, fillColor=BLUE,
                 textAnchor="middle"))
    d.add(String(380, 188, "RADIO SIDE (isolated)", fontName="Helvetica-Bold",
                 fontSize=7.5, fillColor=AMBER, textAnchor="middle"))
    d.add(Line(258, 14, 258, 184, strokeColor=AMBER, strokeWidth=1,
               strokeDashArray=[4, 3]))
    d.add(String(258, 5, "galvanic isolation barrier",
                 fontName="Helvetica-Oblique", fontSize=6.5, fillColor=AMBER,
                 textAnchor="middle"))
    # (label, y, left box, mid box or None, iso part, iso sub, right box,
    #  direction: +1 = gateway->radio, -1 = radio->gateway)
    rows = [
        ("RX audio", 152, "Codec LINE IN (L)", "pad 10K / 10K",
         "T1", "600:600", "Radio speaker / line out", -1),
        ("TX audio", 108, "Codec LINE OUT (L)", "604R level set",
         "T2", "600:600", "Radio mic input", +1),
        ("PTT key", 64, "MCU PD8 via 330R", None,
         "U6", "PC817", "PTT key / return", +1),
        ("COR sense", 20, "MCU PD10 (10K PU)", None,
         "U7", "PC817", "Squelch / busy out", -1),
    ]
    for name, y, left, mid, iso, iso_sub, right, dirn in rows:
        yc = y + 14
        d.add(String(4, yc + 12, name, fontName="Helvetica-Bold", fontSize=7.5,
                     fillColor=NAVY))
        box(d, 56, y, 100, 28, left, fill=SKY, stroke=BLUE, fs=7)
        box(d, 236, y, 44, 28, iso, [iso_sub], fill=AMBER_L, stroke=AMBER,
            fs=7.5, sub_fs=6)
        box(d, 314, y, 112, 28, right, fill=white, stroke=AMBER, fs=7)
        if mid:
            box(d, 170, y, 54, 28, mid, fill=LIGHT, stroke=SLATE, fs=6.2)
            seg = [(156, 170), (224, 236), (280, 314)]
        else:
            seg = [(156, 236)] if True else []
            seg = [(156, 236), (280, 314)]
        for xa, xb in seg:
            if dirn > 0:
                arrow(d, xa, yc, xb, yc, color=SLATE if xb <= 258 else AMBER)
            else:
                arrow(d, xb, yc, xa, yc, color=SLATE if xa < 258 else AMBER)
    return d


def diagram_firmware():
    W, H = 493, 150
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=white, strokeColor=None))
    y1, y2 = 92, 20
    bh = 36
    # uplink row (radio -> IP)
    d.add(String(4, y1 + bh + 8, "Radio → IP (uplink)", fontName="Helvetica-Bold",
                 fontSize=7.5, fillColor=NAVY))
    box(d, 4, y1, 74, bh, "SAI DMA", ["stereo 16-bit", "8/16 kHz"], fill=SKY,
        stroke=BLUE, fs=7.5)
    box(d, 102, y1, 84, bh, "DSP", ["HPF 300 Hz · AGC", "HF noise reduction"],
        fill=LIGHT, stroke=SLATE, fs=7.5)
    box(d, 210, y1, 84, bh, "Encoder", ["Opus 16 kbit/s", "or G.711 µ-law"],
        fill=LIGHT, stroke=SLATE, fs=7.5)
    box(d, 318, y1, 84, bh, "RTP pack", ["+ PTT/SQU bits", "hdr extension"],
        fill=LIGHT, stroke=SLATE, fs=7.5)
    box(d, 426, y1, 62, bh, "lwIP", ["UDP · DHCP"], fill=SKY, stroke=BLUE,
        fs=7.5)
    for xa, xb in ((78, 102), (186, 210), (294, 318), (402, 426)):
        arrow(d, xa, y1 + bh / 2, xb, y1 + bh / 2)
    # downlink row (IP -> radio)
    d.add(String(4, y2 + bh + 8, "IP → Radio (downlink)", fontName="Helvetica-Bold",
                 fontSize=7.5, fillColor=NAVY))
    box(d, 4, y2, 74, bh, "lwIP", ["UDP recv"], fill=SKY, stroke=BLUE, fs=7.5)
    box(d, 102, y2, 84, bh, "Jitter buffer", ["adaptive", "40-120 ms"],
        fill=LIGHT, stroke=SLATE, fs=7.5)
    box(d, 210, y2, 84, bh, "Decoder", ["Opus / G.711"], fill=LIGHT,
        stroke=SLATE, fs=7.5)
    box(d, 318, y2, 84, bh, "SAI DMA out", ["codec DAC", "L=VHF R=HF"],
        fill=LIGHT, stroke=SLATE, fs=7.5)
    box(d, 426, y2, 62, bh, "PTT logic", ["key radio", "via opto"],
        fill=AMBER_L, stroke=AMBER, fs=7.5)
    for xa, xb in ((78, y2), (186, y2), (294, y2), (402, y2)):
        arrow(d, xa, y2 + bh / 2, xa + 24, y2 + bh / 2)
    return d


# ---------------------------------------------------------------- page furniture
def on_content_page(canv, doc):
    canv.saveState()
    canv.setStrokeColor(LINE)
    canv.setLineWidth(0.6)
    canv.line(MARGIN, PAGE_H - 14 * mm, PAGE_W - MARGIN, PAGE_H - 14 * mm)
    canv.setFont("Helvetica", 7.5)
    canv.setFillColor(SLATE)
    canv.drawString(MARGIN, PAGE_H - 12.2 * mm, DOC_TITLE)
    canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 12.2 * mm,
                         "Rev A · " + date.today().strftime("%d %b %Y"))
    canv.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    canv.setFont("Helvetica", 7.5)
    canv.drawString(MARGIN, 9.5 * mm,
                    "Prototype / experimental — not a certified avionics article")
    canv.drawRightString(PAGE_W - MARGIN, 9.5 * mm, f"Page {doc.page}")
    canv.restoreState()


def on_cover_page(canv, doc):
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, PAGE_H - 118 * mm, PAGE_W, 118 * mm, stroke=0, fill=1)
    canv.setFillColor(HexColor("#20456B"))
    canv.rect(0, PAGE_H - 122 * mm, PAGE_W, 4 * mm, stroke=0, fill=1)
    canv.setFillColor(AMBER)
    canv.rect(0, PAGE_H - 123.6 * mm, PAGE_W, 1.6 * mm, stroke=0, fill=1)

    canv.setFillColor(HexColor("#9FB8D0"))
    canv.setFont("Helvetica-Bold", 10)
    canv.drawString(MARGIN, PAGE_H - 40 * mm, "DESIGN DOCUMENT · REV A")
    canv.setFillColor(white)
    canv.setFont("Helvetica-Bold", 27)
    canv.drawString(MARGIN, PAGE_H - 54 * mm, "ATC Radio-over-IP Gateway")
    canv.setFont("Helvetica", 14)
    canv.setFillColor(HexColor("#D3E1EE"))
    canv.drawString(MARGIN, PAGE_H - 64 * mm,
                    "Airborne VHF + HF RoIP over Starlink / aircraft IP")
    canv.setFont("Courier", 9.5)
    canv.setFillColor(HexColor("#9FB8D0"))
    canv.drawString(MARGIN, PAGE_H - 80 * mm,
                    "Pilot headset > gateway > Starlink > ATC IP network > controller")
    canv.setFont("Helvetica", 9.5)
    canv.setFillColor(HexColor("#D3E1EE"))
    y = PAGE_H - 96 * mm
    for line in (
            "STM32H743  ·  LAN8742A Ethernet  ·  TLV320AIC23B stereo codec",
            "Transformer-isolated audio  ·  opto PTT / COR  ·  28 V aircraft bus",
    ):
        canv.drawString(MARGIN, y, line)
        y -= 6.5 * mm

    # meta block lower page
    canv.setFillColor(INK)
    meta = [
        ("Project", "ATC RoIP Gateway (VHF + HF, airborne)"),
        ("Revision", "A — schematic release"),
        ("Date", date.today().strftime("%d %B %Y")),
        ("Prepared by", "eng.ahmad@gmail.com · generated with KiCad 10"),
        ("Design status", "ERC clean · netlist verified · PCB routed, 0 DRC electrical"),
        ("Classification", "Prototype / experimental — no TSO, DO-160, DO-178C"),
    ]
    y = PAGE_H - 148 * mm
    canv.setStrokeColor(LINE)
    canv.setLineWidth(0.6)
    for k, v in meta:
        canv.setFont("Helvetica-Bold", 9.5)
        canv.setFillColor(NAVY)
        canv.drawString(MARGIN, y, k)
        canv.setFont("Helvetica", 9.5)
        canv.setFillColor(INK)
        canv.drawString(MARGIN + 40 * mm, y, v)
        canv.line(MARGIN, y - 2.6 * mm, PAGE_W - MARGIN, y - 2.6 * mm)
        y -= 9 * mm
    canv.setFont("Helvetica", 8)
    canv.setFillColor(SLATE)
    canv.drawString(MARGIN, 20 * mm,
                    "Appendix A contains the full KiCad schematic set (6 sheets, A3).")
    canv.restoreState()


# ---------------------------------------------------------------- content
def P(text, style=st_body):
    return Paragraph(text, style)


def bullets(items):
    return [Paragraph(f"•  {t}", st_bullet) for t in items]


def build_body():
    frame = Frame(MARGIN, 18 * mm, USABLE, PAGE_H - 38 * mm, id="f")
    cover_frame = Frame(MARGIN, 15 * mm, USABLE, PAGE_H - 30 * mm, id="c")
    doc = BaseDocTemplate(BODY_PDF, pagesize=A4,
                          title=DOC_TITLE, author="ATC RoIP Gateway Project")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame], onPage=on_cover_page),
        PageTemplate(id="Content", frames=[frame], onPage=on_content_page),
    ])

    el = []
    el.append(NextPageTemplate("Content"))
    el.append(Spacer(1, 1))       # cover has no flowable content
    el.append(PageBreak())

    # 1 -----------------------------------------------------------------
    el.append(P("1   Executive summary", st_h1))
    el.append(P(
        "This document specifies an airborne <b>Radio-over-IP (RoIP) gateway</b> "
        "that bridges two aircraft transceivers — a VHF COM and an HF radio — "
        "to an IP network carried by a Starlink aviation terminal. Voice is "
        "streamed as RTP with push-to-talk (PTT) and squelch/COR signaling in the "
        "style of EUROCAE ED-137, so a remote operator or ATC-side voice system "
        "can key and monitor the aircraft radios from anywhere on the network."))
    el.append(P(
        "A market survey (Section 2) found no existing certified product with this "
        "scope: ground-side ATC VoIP is mature and standardized (ED-137), airborne "
        "VHF relays exist only in the UAV/BVLOS niche, and no airborne HF RoIP "
        "gateway was found at all. The hardware here fills that gap at "
        "prototype level: a single PCB built around an STM32H743 microcontroller, "
        "a LAN8742A Ethernet PHY, and a TLV320AIC23B stereo codec whose left and "
        "right channels carry the VHF and HF radios respectively, with full "
        "galvanic isolation toward both radios."))
    el.append(P(
        "The complete schematic set was designed in <b>KiCad</b> (six hierarchical "
        "sheets, Appendix A), passes electrical rule check with zero errors and "
        "zero warnings, and its netlist has been machine-verified on fourteen "
        "critical signal paths."))

    el.append(P("2   Market context — what exists today", st_h1))
    el.append(tbl(
        ["Segment", "Status", "Notes"],
        [["Ground ATC RoIP", "Mature, standardized",
          "EUROCAE ED-137 (SIP + RTP with PTT/SQU header extensions); deployed "
          "under SESAR / FAA VoICE; vendors: R&amp;S, Frequentis, Jotron."],
         ["Airborne VHF RoIP", "Niche (UAV / BVLOS)",
          "Orbit Airborne Radio Gateway, Mimer SoftRadio, SyTech: remote pilot "
          "talks to ATC through a VHF radio on the UAV via datalink / satcom."],
         ["Airborne HF RoIP", "Not found",
          "HF-over-IP exists only at ground stations of oceanic networks. "
          "A genuine product gap."],
         ["Voice over Starlink", "Not certified",
          "Starlink carries broadband / VoIP; certified long-range voice remains "
          "SATVOICE (Inmarsat / Iridium), itself still an HF backup, not a "
          "replacement."]],
        [82, 92, USABLE - 174]))
    el.append(Spacer(1, 6))
    el.append(P(
        "Target applications, in order of practicality: (1) UAS / optionally "
        "piloted aircraft where the remote pilot keys the aircraft radios over "
        "Starlink; (2) flight test and special-mission audio streaming and "
        "recording; (3) experimental-aircraft backup audio paths; (4) airborne "
        "HF remote-operation trials."))

    # 3 -----------------------------------------------------------------
    el.append(P("3   System architecture", st_h1))
    el.append(diagram_system())
    el.append(P("Figure 1 — End-to-end signal chain", st_caption))
    el.append(P(
        "The gateway sits on the aircraft LAN behind the Starlink router and "
        "terminates an RTP session per radio channel. On the radio side it "
        "behaves like a remote operator position: it injects microphone audio "
        "and keys PTT, and it captures receiver audio together with the radio's "
        "carrier-operated squelch (COR) state. Latency budget over Starlink is "
        "typically 25–60 ms one-way plus jitter, which the adaptive jitter "
        "buffer absorbs; this is acceptable for remote-pilot and monitoring use "
        "but is one of the reasons tactical ATC certification is a long-term "
        "goal rather than a rev-A claim."))

    # 4 -----------------------------------------------------------------
    el.append(PageBreak())
    el.append(P("4   Hardware design", st_h1))
    el.append(diagram_board())
    el.append(P("Figure 2 — Board block diagram (blocks map 1:1 to schematic sheets)",
                st_caption))
    el.append(P("4.1  Processor and network", st_h2))
    el.append(P(
        "The STM32H743VIT6 (Cortex-M7, 480 MHz, LQFP-100) provides the Ethernet "
        "MAC, the SAI serial-audio interface, and enough compute headroom for "
        "lwIP plus two simultaneous Opus encoder/decoder pairs. The LAN8742A "
        "PHY connects over RMII; it is strapped (nINTSEL low) to source the "
        "50 MHz RMII reference clock, saving a MCU clock output. The RJ45 jack "
        "has integrated magnetics; its center taps are biased from +3V3 through "
        "a ferrite bead per the PHY's drive scheme."))
    el.append(P("4.2  Audio path", st_h2))
    el.append(P(
        "A single TLV320AIC23B stereo codec serves both radios: <b>left channel "
        "= VHF, right channel = HF</b>, in both directions, giving perfectly "
        "aligned sampling from one SAI port. Airband AM and HF SSB voice occupy "
        "300–2500 Hz, so 8 kHz sampling suffices (16 kHz recommended with "
        "Opus). The codec is controlled over I2C at address 0x1A and runs as "
        "I2S slave from SAI1 (MCLK, BCLK, FS)."))
    el.append(P("4.3  Power", st_h2))
    el.append(P(
        "The 28 V DC aircraft bus enters through a fuse, a series Schottky for "
        "reverse polarity, and an SMCJ33A transient clamp. An LM2576HV-5.0 buck "
        "(60 V maximum input) survives bus transients and feeds an AMS1117-3.3 "
        "LDO. Ferrite beads split a dedicated +3.3VA / GNDA analog domain for "
        "the codec. Full DO-160 section 16/17 power quality (200 ms holdup, "
        "surge waveforms) requires an additional upstream stage and is "
        "deliberately out of scope for rev A."))
    el.append(P("4.4  Key components", st_h2))
    el.append(tbl(
        ["Block", "Part", "Function"],
        [["MCU", "STM32H743VIT6", "lwIP + RTP + codec control, RMII MAC, SAI"],
         ["Ethernet PHY", "LAN8742A", "RMII, REF_CLK-out strap, 1.5 kΩ MDIO pull-up"],
         ["RJ45", "Amphenol RJMG1BD3B8K1ANR", "Integrated magnetics + LEDs"],
         ["Codec", "TLV320AIC23BPW", "Stereo ADC/DAC, I2S slave, I2C 0x1A"],
         ["Audio isolation", "600:600 Ω transformers ×4",
          "RX + TX per channel (DIP-4 placeholder footprint)"],
         ["PTT / COR", "PC817 ×4", "Opto key-out and squelch sense per channel"],
         ["Buck", "LM2576HVS-5.0", "28 V → 5 V, 3 A, 60 V rated"],
         ["LDO", "AMS1117-3.3", "5 V → 3.3 V digital"],
         ["Protection", "SS54 + SMCJ33A", "Reverse polarity + transient clamp"]],
        [78, 128, USABLE - 206]))

    # 5 -----------------------------------------------------------------
    el.append(PageBreak())
    el.append(P("5   Radio interface (isolation barrier)", st_h1))
    el.append(diagram_channel())
    el.append(P("Figure 3 — One radio channel (VHF shown; HF identical)", st_caption))
    el.append(P(
        "Every line to the radios crosses a galvanic isolation barrier, killing "
        "ground loops between the gateway, the airframe, and the radio installs. "
        "Receive and transmit audio each pass through a 600:600 Ω transformer; "
        "the receive side is padded 10 kΩ/10 kΩ before the codec line input "
        "and the transmit side has a 604 Ω series level-set resistor "
        "(trim per radio's mic sensitivity). PTT is keyed by a PC817 "
        "optocoupler whose collector–emitter closes the radio's PTT line to its "
        "own ground return (≤50 mA / 35 V — fit a relay or MOSFET buffer for HF "
        "couplers that key more current, and a TVS across the key line for "
        "antenna-tuner kick-back). The radio's squelch/busy output drives a "
        "second opto through 4.7 kΩ, giving the firmware a true COR input; "
        "DSP-based VOX is the fallback when a radio provides no COR line."))
    el.append(P("5.1  DB25 radio connector (J5)", st_h2))
    el.append(tbl(
        ["Signal", "VHF pins", "HF pins", "Notes"],
        [["RX audio hi / lo", "1 / 14", "6 / 19", "From radio speaker or 600 Ω line out"],
         ["Mic audio hi / lo", "2 / 15", "7 / 20", "To radio mic input, level set by series R"],
         ["PTT key / return", "3 / 16", "8 / 21", "Opto collector / emitter, isolated"],
         ["COR hi / lo", "4 / 17", "9 / 22", "Radio squelch/busy output drives opto LED"],
         ["Chassis / common", "13, 25", "13, 25", "Plus connector shell"]],
        [92, 55, 55, USABLE - 202]))

    el.append(P("5.2  MCU pin allocation", st_h2))
    el.append(tbl(
        ["Function", "Pins"],
        [["RMII to LAN8742A",
          "PA1 REF_CLK · PA2 MDIO · PC1 MDC · PA7 CRS_DV · PC4/PC5 RXD0/1 · "
          "PB11 TX_EN · PB12/PB13 TXD0/1 · PE10 PHY reset"],
         ["SAI1 to codec",
          "PE2 MCLK · PE5 BCLK · PE4 FS (LRCIN+LRCOUT) · PE6 → DIN · PE3 ← DOUT"],
         ["I2C1 codec control", "PB6 SCL · PB7 SDA (4.7 kΩ pull-ups)"],
         ["PTT outputs", "PD8 VHF · PD9 HF (330 Ω to opto LED)"],
         ["COR inputs", "PD10 VHF · PD11 HF (10 kΩ pull-ups, opto pulls low)"],
         ["Debug / console", "SWD PA13/PA14 (J2) · USART1 PA9/PA10 (J3)"],
         ["Status LEDs", "PD12 · PD13 · PD14"]],
        [108, USABLE - 108]))

    # 6 -----------------------------------------------------------------
    el.append(PageBreak())
    el.append(P("6   Firmware architecture", st_h1))
    el.append(diagram_firmware())
    el.append(P("Figure 4 — Firmware dataflow (per radio channel)", st_caption))
    el.extend(bullets([
        "<b>Transport:</b> RTP over UDP, 20 ms frames; Opus 16 kbit/s VBR per "
        "channel, or G.711 µ-law 64 kbit/s for ED-137B Radio-profile "
        "compatibility. PTT and squelch travel in the RTP header extension "
        "(ED-137 R2S style).",
        "<b>Session:</b> statically configured peer for rev A; SIP session "
        "management (full ED-137 signaling) as a later increment.",
        "<b>Jitter buffer:</b> adaptive 40–120 ms, sized for Starlink jitter.",
        "<b>HF channel extras:</b> AGC, noise reduction, 300–2700 Hz bandpass, "
        "and a key-line interlock delay for antenna-coupler tune cycles.",
        "<b>VOX fallback</b> when no COR line is wired to a radio.",
        "<b>Config:</b> UART console + DHCP; small HTTP status page later."]))

    el.append(P(
        "This stack is implemented in the <b>firmware/</b> tree: ED-137-style "
        "RTP with the PTT/SQU header extension and R2S keepalive "
        "(rtp_ed137.c), a minimal SIP endpoint answering INVITE/ACK/BYE/"
        "OPTIONS with WG67-flavoured SDP (sip_mini.c), G.711 u-law (g711.c), "
        "the TLV320AIC23B driver (aic23.c), SAI DMA streaming (sai_stream.c), "
        "per-channel jitter buffer and PTT/COR logic (roip_chan.c), and HPF/"
        "AGC/VOX conditioning (voxagc.c). It builds with CMake + "
        "arm-none-eabi-gcc against the official STM32CubeH7 HAL/lwIP and "
        "flashes over SWD (header J2) with STM32CubeProgrammer (flash.ps1) "
        "or via the ROM bootloader on the J3 UART."))

    el.append(PageBreak())
    el.append(P("7   PCB implementation", st_h1))
    img_path = os.path.join(HW, "board-top.png")
    if os.path.exists(img_path):
        img = Image(img_path, width=USABLE * 0.84,
                    height=USABLE * 0.84 * 0.75)
        img.hAlign = "CENTER"
        el.append(img)
        el.append(P("Figure 5 - Routed board, top side (125 x 95 mm, 4-layer)",
                    st_caption))
    el.append(P(
        "The board is a 125 x 95 mm four-layer design: signals on the outer "
        "layers, solid GND (In1) and +3V3 (In2) planes inside. Floorplan: "
        "RJ45 with integrated magnetics and the LAN8742A PHY on the left "
        "edge, STM32H743 in the centre, TLV320AIC23B codec to its right, and "
        "the isolation zone - four 600 Ohm transformers, four PC817 "
        "optocouplers and the DB25 radio connector - along the right edge; "
        "the 28 V power chain runs along the bottom from the input terminal "
        "block through the buck and LDO. Routing: Freerouting autorouter "
        "constrained to the outer layers, then scripted collision-checked "
        "power fanout (86+ plane-stitching vias) and hand-verified repairs "
        "in congested areas. Rules: 0.2 mm min track, 0.15 mm clearance, "
        "0.45/0.2 mm min via - standard 4-layer fab capability."))
    el.append(P(
        "Manufacturing outputs (hardware/atc-roip-gateway/fab/): Gerbers, "
        "Excellon drill + map, pick-and-place CSV, and a ready-to-upload "
        "Gerber ZIP."))

    el.append(P("8   Bill of materials", st_h1))
    el.append(P(
        "Complete BOM: docs/BOM.csv - 40 line items, 100 components, with "
        "manufacturer part numbers. Summary:"))
    import csv as _csv
    bom_rows = []
    try:
        with open(os.path.join(ROOT, "docs", "BOM.csv"),
                  encoding="utf-8-sig") as f:
            rd = _csv.reader(f)
            next(rd)
            for row in rd:
                refs, qty, value, desc, mfr, mpnv, fpv, note = row
                if len(refs) > 30:
                    refs = refs[:27] + "..."
                bom_rows.append([refs, qty, value, mpnv])
    except Exception:
        pass
    if bom_rows:
        el.append(tbl(["References", "Qty", "Value", "Manufacturer P/N"],
                      bom_rows, [140, 28, 90, USABLE - 258]))
    el.append(Spacer(1, 6))

    el.append(PageBreak())
    el.append(P("9   Verification", st_h1))
    el.append(P(
        "Schematic, netlist, PCB and fab outputs are machine-generated and "
        "machine-checked; every artifact is reproducible from tools/."))
    el.append(tbl(
        ["Check", "Tool", "Result"],
        [["Electrical rule check (all sheets)", "kicad-cli sch erc",
          "0 errors, 0 warnings"],
         ["Netlist connectivity, 14 critical paths (RMII, SAI, I2C, PTT, "
          "COR, audio, power)", "tools/check_netlist.py", "14 / 14 pass"],
         ["Power rail membership", "netlist audit",
          "+3V3 41 pins, GND 62, GNDA 17, +3.3VA 7, +5V 6"],
         ["PCB connectivity", "kicad-cli pcb drc",
          "0 unconnected pads (fully routed)"],
         ["PCB electrical rules (clearance, shorts, holes, edge)",
          "kicad-cli pcb drc", "0 violations"],
         ["PCB cosmetics", "kicad-cli pcb drc",
          "13 silkscreen notes (connector artwork; fab-clipped)"]],
        [USABLE - 250, 120, 130]))
    el.append(Spacer(1, 6))


    el.append(P("10   Compliance and regulatory position", st_h1))
    el.extend(bullets([
        "<b>ED-137:</b> ED-137 is a protocol standard — compliance is earned in "
        "firmware and by conformance test. This hardware is <i>ED-137-ready</i>: "
        "G.711-capable 8 kHz codec, Ethernet, and real PTT/COR signal paths. "
        "Validation against an ED-137 test set (e.g. GL MAPS) is a firmware "
        "milestone.",
        "<b>Certification:</b> rev A is prototype/experimental hardware — no TSO "
        "authorization, no DO-160 qualification, no DO-178C/DO-254 artifacts. "
        "Suitable for bench, UAS, and experimental-category use.",
        "<b>Spectrum:</b> the gateway only keys an already-certified transceiver; "
        "transmissions on ATC frequencies require an appropriately licensed "
        "radio and operator.",
        "<b>Operational:</b> ATC voice over Starlink is not an approved substitute "
        "for required VHF/HF/SATVOICE equipage in controlled airspace."]))

    el.append(P("11   Next steps", st_h1))
    el.extend(bullets([
        "Review radio-side levels against the specific transceivers (mic "
        "sensitivity, PTT current, HF coupler behaviour).",
        "Order boards from the fab ZIP; assemble, bring up power, then SWD. "
        "",
        "Firmware bring-up on NUCLEO-H743ZI + codec breakout before board spin.",
        "Bench test against an ED-137 radio emulator; then live-radio testing "
        "on the bench with dummy loads."]))

    el.append(Spacer(1, 10))
    el.append(P("Appendix A — Schematic sheets", st_h1))
    el.append(P(
        "The following six A3 sheets are the complete rev A schematic as "
        "plotted from KiCad: root/index, power supply, MCU, Ethernet, audio "
        "codec, and radio interface. Every pin carries a drawn wire stub with "
        "its net label; the netlist is the authoritative artifact "
        "and is what the Section 9 checks validate."))

    doc.build(el)


def merge():
    writer = PdfWriter()
    for page in PdfReader(BODY_PDF).pages:
        writer.add_page(page)
    for page in PdfReader(SCH_PDF).pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": DOC_TITLE,
                         "/Author": "ATC RoIP Gateway Project"})
    with open(OUT_PDF, "wb") as f:
        writer.write(f)
    print("wrote", OUT_PDF)


if __name__ == "__main__":
    build_body()
    merge()
