# ATC RoIP Gateway (VHF + HF, airborne)

Radio-over-IP gateway for aircraft ATC radios: bridges a VHF COM and an HF
transceiver to an IP network (Starlink aviation terminal) with an ED-137-style
RTP audio + PTT/COR stream.

```
Pilot/remote op ⇄ RTP over IP (Starlink) ⇄ [this gateway] ⇄ VHF COM + HF transceivers
```

## Deliverables

| Item | Where | Status |
|---|---|---|
| **Design document (PDF)** | `ATC-RoIP-Gateway-Design-Document.pdf` | 16 pages: study, diagrams, PCB, BOM, verification + schematic appendix |
| **Market study** | `docs/01-market-study.md` | sourced |
| **Design spec** | `docs/02-design-spec.md` | rev A |
| **Schematics** | `hardware/atc-roip-gateway/*.kicad_sch` | ERC 0 errors / 0 warnings, wired stubs + net labels |
| **PCB (4-layer, 125×95 mm)** | `hardware/atc-roip-gateway/atc-roip-gateway.kicad_pcb` | fully routed, 0 unconnected, 0 electrical DRC |
| **Fab outputs** | `hardware/atc-roip-gateway/fab/` | Gerber ZIP, drill, pick-and-place |
| **BOM** | `docs/BOM.csv` | 40 line items, 100 parts, MPNs assigned |
| **Firmware** | `firmware/` | ED-137-style stack (SIP + RTP/PTT/SQU + G.711), CMake, flash script |
| **Generators** | `tools/` | schematic/PCB/BOM/doc generation + checks (reproducible) |

## Hardware summary
| Block | Part |
|---|---|
| MCU | STM32H743VIT6 (Ethernet MAC + SAI, runs lwIP + RTP) |
| Ethernet | LAN8742A RMII PHY + magnetics-integrated RJ45 |
| Audio | TLV320AIC23B stereo codec — Left = VHF, Right = HF |
| Radio isolation | 600:600 Ω transformers (RX/TX ×2), PC817 optos (PTT + COR ×2) |
| Radio connector | DB25 (pinout in design spec §5.1) |
| Power | 28 V DC bus → LM2576HV-5.0 buck → AMS1117-3.3, split analog rail |

## Regenerating everything
```bash
python tools/design.py            # schematics
python tools/make_bom.py          # BOM from netlist
python tools/make_design_doc.py   # design document PDF
# PCB: tools/make_pcb.py (placement) + Freerouting + tools/power_fanout_final.py
```

## Status / caveats
- Rev A prototype: not TSO'd, no DO-160 qualification, no DO-178C artifacts.
- ED-137: hardware + firmware structured for the ED-137B Radio profile; exact
  extension bit-fields and SDP attributes must be verified against the
  licensed EUROCAE text + a conformance tool before claiming compliance.
- Transformer footprint (DIP-4) and DB25 gender are placeholders — confirm
  against the chosen audio transformer and aircraft harness.
- Firmware builds against STM32CubeH7 (user fetches; see `firmware/README.md`)
  and needs the four board-config files copied per `firmware/src/config/README.md`.
