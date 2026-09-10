# ATC RoIP Gateway — Design Specification

Airborne Radio-over-IP gateway that bridges **two aircraft transceivers (VHF COM +
HF)** to an **IP network (Starlink aviation terminal / aircraft LAN)** using an
ED-137-style RTP audio + PTT/COR signaling stream.

```
                             ┌─────────────────────────────────────────────┐
 VHF COM ──audio/PTT/COR──►  │  [radio_if]      [audio]      [mcu]   [eth] │
 HF XCVR ──audio/PTT/COR──►  │  transformers → TLV320AIC23 → STM32H7 → PHY ├──RJ45──► Starlink router
                             │  + PC817 optos    stereo codec  RTP/Opus    │           │
 28V DC bus ───────────────► │  [power] 28V → 5V buck → 3.3V / 3.3VA       │           ▼
                             └─────────────────────────────────────────────┘   ATC IP network / remote op
```

## KiCad project
`hardware/atc-roip-gateway/` — KiCad 8+ format (opens in KiCad 8/9/10).

| Sheet | File | Content |
|---|---|---|
| Root | `atc-roip-gateway.kicad_sch` | block notes + sheet index |
| Power | `power.kicad_sch` | 28 V bus input, protection, 5 V buck, 3.3 V LDO, analog rail split |
| MCU | `mcu.kicad_sch` | STM32H743VIT6, crystal, SWD, UART, PTT/COR GPIO, status LEDs |
| Ethernet | `ethernet.kicad_sch` | LAN8742A RMII PHY, 25 MHz crystal, magnetics-integrated RJ45 |
| Audio | `audio.kicad_sch` | TLV320AIC23B stereo codec (L = VHF, R = HF), coupling networks |
| Radio IF | `radio_if.kicad_sch` | 600 Ω isolation transformers ×4, PC817 optos ×4, DB25 |

Validation: `kicad-cli sch erc` — **0 errors, 0 warnings**; netlist connectivity
machine-checked (`tools/check_netlist.py`, 14 signal-path assertions + rail sizes).

The schematics are machine-generated (`tools/design.py` + `tools/kicad_gen.py`):
every pin carries a global label or power symbol rather than drawn wires. To
modify, edit `tools/design.py` and re-run `python tools/design.py`.

## Key design decisions

### One stereo codec, two radios
The TLV320AIC23B is a stereo 16/20/24/32-bit codec. **Left channel = VHF, right
channel = HF** for both ADC (radio RX audio → IP) and DAC (IP → radio mic input).
One I2S/SAI port on the MCU serves both radios with perfect sample alignment.
Airband AM and HF SSB voice are 300–2500 Hz; 8 kHz Fs suffices, 16 kHz recommended
with Opus.

### Galvanic isolation on every radio line
- **Audio:** 600:600 Ω transformers (T1–T4) on RX and TX paths of both channels —
  kills ground loops between the gateway and radios/audio panel (footprints are
  DIP-4 placeholders; fit e.g. Triad SP-66/TY-141P class parts).
- **PTT:** PC817 opto (U6/U8); collector–emitter keys the radio's PTT line to its
  own ground return (≤ 50 mA, ≤ 35 V — fit a transistor buffer or relay for HF
  couplers that key more current, and a TVS across the key line for tuner kick-back).
- **COR/squelch sense:** PC817 (U7/U9) driven by the radio's squelch/busy output
  through 4.7 kΩ; lets firmware do true carrier-operated squelch signaling in the
  RTP stream (VOX in DSP is the fallback when a radio has no COR output).

### STM32H743 + LAN8742A
480 MHz Cortex-M7 with hardware Ethernet MAC and SAI. Enough headroom for lwIP +
RTP + two Opus encoder/decoder pairs (or G.711 μ-law for ED-137 compatibility).
PHY strapped `nINTSEL` low → REF_CLK-out mode: the PHY sources the 50 MHz RMII
clock into PA1. MDIO pulled up 1.5 kΩ; PHY reset on PE10 with RC.

### Power: 28 V aircraft bus
Fuse → series Schottky (reverse polarity) → SMCJ33A TVS → **LM2576HV-5.0**
(60 V max input survives bus transients) → 5 V → AMS1117 → 3.3 V digital.
Ferrite beads split **+3.3VA/GNDA** for the codec analog side.
*DO-160 §16/17 compliance needs an upstream surge/holdup stage (e.g. active
clamp + holdup capacitance for 200 ms power interruption) — out of scope of rev A.*

## MCU pin allocation

| Function | Pins |
|---|---|
| RMII to LAN8742A | PA1 REF_CLK, PA2 MDIO, PC1 MDC, PA7 CRS_DV, PC4/PC5 RXD0/1, PB11 TX_EN, PB12/PB13 TXD0/1, PE10 PHY reset |
| SAI1 to codec | PE2 MCLK, PE5 BCLK, PE4 FS (LRCIN+LRCOUT), PE6 → DIN, PE3 ← DOUT |
| I2C1 (codec ctrl, addr 0x1A) | PB6 SCL, PB7 SDA (4.7 kΩ pull-ups) |
| PTT out | PD8 VHF, PD9 HF (→ 330 Ω → opto LED) |
| COR in | PD10 VHF, PD11 HF (10 kΩ pull-ups, opto pulls low) |
| Console / debug | USART1 PA9/PA10 (J3), SWD PA13/PA14 (J2) |
| Status LEDs | PD12/PD13/PD14 |

## DB25 radio connector (J5)

| Signal | VHF | HF | Notes |
|---|---|---|---|
| RX audio (hi/lo) | 1 / 14 | 6 / 19 | from radio speaker/600 Ω line out |
| Mic audio (hi/lo) | 2 / 15 | 7 / 20 | to radio mic input, level set by R25/R30 + trim |
| PTT (key/return) | 3 / 16 | 8 / 21 | opto collector/emitter, isolated |
| COR/squelch (hi/lo) | 4 / 17 | 9 / 22 | radio busy/squelch output drives opto LED |
| Chassis/common | 13, 25, shell | | |

## Firmware plan (not in this repo yet)
1. **Transport:** RTP over UDP; 20 ms frames; Opus @ 16 kbit/s VBR per channel
   (or G.711 μ-law 64 kbit/s for ED-137B Radio profile compatibility).
   PTT/squelch signaling in RTP header extension per ED-137 (R2S/PTT bits), or a
   simple side-channel UDP keepalive protocol for point-to-point use.
2. **Session:** static peer config first; SIP (ED-137 signalling) later.
3. **Jitter buffer:** adaptive 40–120 ms — sized for Starlink jitter.
4. **HF channel extras:** AGC, noise reduction, 300–2700 Hz bandpass, squelch DSP;
   key-line interlock delay for antenna coupler tune cycles.
5. **VOX fallback** when no COR line is wired.
6. **Config:** USART console + DHCP; later a tiny HTTP config page.

## Regulatory / safety notes
- This rev A design is **experimental / prototype** hardware: no TSO authorization,
  no DO-160 qualification, no DO-178C/DO-254 artifacts. Suitable for bench work,
  UAS, and experimental-category aircraft where the installer accepts responsibility.
- Transmitting on ATC frequencies requires an appropriately licensed radio and
  operator; the gateway only keys an already-certified transceiver.
- ATC voice relayed over Starlink is **not** an approved substitute for required
  VHF/HF/SATVOICE equipage in controlled airspace.

## Next steps
1. Review schematic PDF; adjust radio-side levels for the specific transceivers
   (e.g. mic input sensitivity, whether HF PTT needs a relay).
2. PCB layout (4-layer: SIG / GND / PWR / SIG; keep RMII short, isolate the
   transformer/opto zone from digital).
3. Firmware bring-up on a NUCLEO-H743ZI + codec breakout before spinning boards.
4. Bench test against an ED-137 test tool (GL MAPS or open-source RTP tooling).
