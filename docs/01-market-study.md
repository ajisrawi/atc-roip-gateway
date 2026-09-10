# Market Study — Radio-over-IP Gateways for Airborne ATC Radio (VHF & HF)

**Date:** September 2026
**Question:** Does a Radio-over-IP (RoIP) gateway currently exist for *airborne* ATC
radios (VHF and HF), suitable for the architecture:

```
Pilot headset → Aircraft audio/RoIP gateway → Starlink → ATC IP network → Controller
```

## Summary answer

| Segment | Exists today? | Notes |
|---|---|---|
| **Ground-side ATC RoIP (VHF/HF ground stations)** | **Yes — mature & standardized** | EUROCAE **ED-137** (now rev C) defines VoIP for ATM: Controller Working Position (CWP), Ground Radio Station (GRS), Radio Media Gateway (RMG). Deployed worldwide (SESAR, FAA VoICE, ICAO Doc 9896). Vendors: Rohde & Schwarz, Frequentis, Jotron, GL Communications (test), VOCAL (stacks). |
| **Airborne VHF RoIP — UAV/BVLOS market** | **Yes — niche products** | Gateways that put a VHF airband radio on the aircraft and stream audio + PTT over the UAS datalink (LOS RF, cellular, or satcom) so a remote pilot can talk to ATC: Orbit Communication Systems Airborne Radio Gateway, Mimer SoftRadio, SyTech RoIP gateways. Patents exist for exactly this (e.g. US 9,281,890 — aeronautical radio voice+signaling over satellite IP; US 12,327,479 — ATC voice relay for UAS). |
| **Airborne HF RoIP gateway** | **No commercial product found** | HF-over-IP exists only on the *ground* side (remote HF ground stations of oceanic networks are IP-linked to centers). No airborne HF RoIP gateway product was identified — this is a genuine gap. |
| **ATC voice over Starlink (certified, crewed aviation)** | **No** | Starlink aviation terminals (STC'd on many types) carry generic broadband and VoIP calls, but there is **no certified path for controller–pilot voice over Starlink**. Oceanic/remote voice today is SATVOICE over Inmarsat/Iridium (certified LRCS), used as HF *backup* — and even SATVOICE is not yet accepted as a full HF replacement in most airspace. |

**Conclusion:** the exact product you describe — a single airborne gateway that fronts
both a VHF COM and an HF transceiver and streams them over an aircraft IP/Starlink
link — does **not exist** as a certified commercial product. Its building blocks all
exist (ED-137 on the ground, UAV VHF relay gateways, Starlink aviation broadband), so
a purpose-built gateway is a design gap worth filling — first for experimental /
UAS / flight-test use, since the certification path for crewed IFR use is long.

## What exists in detail

### 1. Ground infrastructure: ED-137 is the standard
EUROCAE WG-67's **ED-137** ("Interoperability Standard for VoIP ATM Components")
defines SIP session setup and RTP audio with PTT/squelch signaling carried in RTP
header extensions. Revisions: ED-137 (2009), A (2010), B (2012), C (2017-2020s).
It is the worldwide direction for ATC voice (SESAR, FAA VoICE program, ICAO Doc
9896). Any airborne gateway should speak an ED-137B/C Radio-profile-compatible
stream so it can plug into ground VCS (Voice Communication Systems) with minimal
adaptation.

### 2. Airborne RoIP today: the UAV/BVLOS niche
- **Orbit Communication Systems** — "Airborne Radio Gateway": ground operators
  access airborne radios over the UAS LOS/BLOS datalink to talk to ATC.
- **Mimer SoftRadio** — drone pilot talks to ATC through a VHF radio mounted on
  the UAV, from anywhere with Internet.
- **SyTech, VOCAL** — general RoIP gateways/stacks used in remote-pilot setups.
- Typical published architecture: VHF transceiver on the aircraft → RoIP gateway →
  audio digitized/compressed (~9.6 kbps) → UDP/RTP → satellite/cellular → ground.

These are VHF-only, mostly for unmanned aircraft, and none is a TSO'd avionics
article for crewed aircraft.

### 3. Long-range voice today: SATVOICE, not RoIP
For oceanic/remote airspace, certified long-range voice is **SATVOICE** via
Inmarsat (Aero H/H+) or Iridium, plus **CPDLC/ADS-C** datalink (FANS 1/A). SATVOICE
is accepted as a Long Range Communication System and HF backup; regulators still
generally require HF where HF is mandated, and CPDLC is not accepted for emergency/
non-routine comms. Iridium safety services are expanding toward enabling HF
relief in MMELs. Starlink has no aviation *safety-services* offering.

### 4. Why the gap exists (and what it means for the design)
- **Latency/QoS:** ED-137 assumes engineered ground networks; Starlink adds ~25–60 ms
  plus jitter and occasional outages — usable for AOC and experimental relay, hard to
  certify for tactical ATC voice today.
- **Certification:** a crewed-aircraft installation needs TSO/ETSO articles, DO-160
  environmental, DO-178C/DO-254 for software/hardware if it becomes required equipment.
  As *supplemental* equipment on experimental / restricted category aircraft (or UAS),
  the bar is far lower.
- **HF specifics:** HF SSB audio (300–2700 Hz, high noise, AGC pumping, tuner key-line
  interlocks) needs DSP conditioning that no off-the-shelf airborne RoIP box provides.

## Use cases for the designed gateway
1. **UAS/optionally-piloted aircraft:** remote pilot on the ground keys the aircraft's
   VHF/HF radios over Starlink — today's strongest commercial demand.
2. **Flight test / special mission:** stream live ATC audio to an ops center;
   record/timestamp both channels.
3. **Backup crew audio path:** pilot headset on the IP side (softphone) reaching the
   aircraft radios if the audio panel path is degraded (experimental aircraft only).
4. **HF trials:** remote HF operation trials (ham/MARS-style remoting is common
   practice on the ground; airborne remoting is unexplored).

## Sources
- [Radio over IP (RoIP) suppliers overview — Unmanned Systems Technology](https://www.unmannedsystemstechnology.com/expo/radio-over-ip-roip/)
- [Mimer SoftRadio RoIP platform, drone pilot ↔ ATC via onboard VHF](https://www.unmannedsystemstechnology.com/2023/06/mimer-softradio-roip-platform-adds-new-vhf-radio-compatibility/)
- [Orbit Communication Systems — Airborne Radio Gateway for UAS (PDF)](https://orbit-cs-usa.com/wp-content/uploads/2021/08/Radio-Gateway-for-UAS-_New_Brand.pdf)
- [SyTech Corporation — radio gateways & remote pilot UAV comms](https://www.sytechcorp.com/radio-gateways)
- [VOCAL — RoIP gateway and ED-137 VoIP ATM software](https://vocal.com/voip/roip/ed-137-voip-air-traffic-management/)
- [GL Communications — ED-137/ED-138 test tools; standard history](https://www.gl.com/test-solutions-for-voip-air-traffic-management.html)
- [Rohde & Schwarz — "ATC on its way to Voice over IP"](https://www.rohde-schwarz.com/us/applications/atc-on-its-way-to-voice-over-ip-application-card_56279-3841.html)
- [US Patent 9,281,890 — aeronautical radio voice & signaling over satellite IP](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9281890)
- [US Patent 12,327,479 — ATC voice relay for UAS over an aviation network](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12327479)
- [OPSGROUP — "The Big SATVOICE Question" (SATVOICE vs HF status)](https://ops.group/blog/the-big-satvoice-question/)
- [AirSatOne — SATVOICE LRCS via Iridium and Inmarsat](https://www.airsatone.com/satvoice-lrcs)
- [FAA AIP ENR 7.2 — oceanic data link / voice procedures](https://www.faa.gov/air_traffic/publications/atpubs/aip_html/part2_enr_section_7.2.html)
- [Pilot Mall — Starlink for general aviation status](https://www.pilotmall.com/blogs/news/high-speed-skies-is-starlink-ready-for-the-general-aviation-cockpit)
- [Survey of IP-based air-to-ground datalink technologies (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0969699724000449)
