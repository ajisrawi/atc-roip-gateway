"""ATC RoIP Gateway - schematic design definition.

Generates the full KiCad project:
  hardware/atc-roip-gateway/atc-roip-gateway.kicad_pro
  hardware/atc-roip-gateway/atc-roip-gateway.kicad_sch   (root)
  hardware/atc-roip-gateway/power.kicad_sch
  hardware/atc-roip-gateway/mcu.kicad_sch
  hardware/atc-roip-gateway/ethernet.kicad_sch
  hardware/atc-roip-gateway/audio.kicad_sch
  hardware/atc-roip-gateway/radio_if.kicad_sch
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from kicad_gen import (SymbolLibrary, Sheet, Part, render_sheet, connect_part,
                       pin_endpoint, new_uuid, fmt)

PROJECT = "atc-roip-gateway"
OUTDIR = os.path.join(os.path.dirname(__file__), "..", "hardware", PROJECT)

R_0603 = "Resistor_SMD:R_0603_1608Metric"
C_0603 = "Capacitor_SMD:C_0603_1608Metric"
C_0805 = "Capacitor_SMD:C_0805_2012Metric"

libdb = SymbolLibrary()
ROOT_UUID = new_uuid()


def tie_power(sheet, pname, x, y):
    sheet.power.append((pname, x, y, 0.0))


def tie_label(sheet, net, x, y, ang=0.0):
    sheet.labels.append((net, x, y, ang))


def pin_pt(part, lib, name, pin_no):
    sym = libdb.get(lib, name)
    for p in sym.pins:
        if p['number'] == pin_no:
            return pin_endpoint(sym, part.x, part.y, p)
    raise KeyError(pin_no)


def build_power():
    sh = Sheet("power.kicad_sch", "Power Supply - 28V Bus Input", PROJECT)
    P = []

    j1 = Part("J1", "Connector_Generic", "Conn_01x02", "28VDC_BUS_IN",
              40, 60, {"1": "VBUS_IN", "2": "#GND"},
              "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal")
    P.append(j1)
    f1 = Part("F1", "Device", "Fuse", "1A", 70, 60,
              {"1": "VBUS_IN", "2": "VBUS_F"}, "Fuse:Fuse_1206_3216Metric")
    P.append(f1)
    # series reverse-polarity Schottky: anode(2)=VBUS_F, cathode(1)=VBUS_PROT
    P.append(Part("D2", "Device", "D_Schottky", "SS54", 90, 60,
                  {"2": "VBUS_F", "1": "VBUS_PROT"},
                  "Diode_SMD:D_SMA"))
    P.append(Part("D1", "Device", "D_TVS", "SMCJ33A", 110, 80,
                  {"1": "VBUS_PROT", "2": "#GND"}, "Diode_SMD:D_SMC"))
    P.append(Part("C1", "Device", "C_Polarized", "100uF/63V", 130, 80,
                  {"1": "VBUS_PROT", "2": "#GND"},
                  "Capacitor_SMD:CP_Elec_8x10"))
    P.append(Part("C2", "Device", "C", "100nF/100V", 142.5, 80,
                  {"1": "VBUS_PROT", "2": "#GND"}, C_0805))
    P.append(Part("U1", "Regulator_Switching", "LM2576HVS-5", "LM2576HVS-5.0",
                  180, 60, {"VIN": "VBUS_PROT", "GND": "#GND",
                            "~{ON}/OFF": "#GND", "OUT": "SW_5V", "FB": "#+5V"},
                  "Package_TO_SOT_SMD:TO-263-5_TabPin3"))
    P.append(Part("D3", "Device", "D_Schottky", "SS54", 180, 90,
                  {"1": "SW_5V", "2": "#GND"}, "Diode_SMD:D_SMA"))
    P.append(Part("L1", "Device", "L", "100uH/3A", 210, 60,
                  {"1": "SW_5V", "2": "#+5V"},
                  "Inductor_SMD:L_12x12mm_H8mm"))
    P.append(Part("C3", "Device", "C_Polarized", "470uF/16V", 230, 60,
                  {"1": "#+5V", "2": "#GND"}, "Capacitor_SMD:CP_Elec_8x10"))
    P.append(Part("C4", "Device", "C", "100nF", 242.5, 60,
                  {"1": "#+5V", "2": "#GND"}, C_0603))
    P.append(Part("U2", "Regulator_Linear", "AMS1117-3.3", "AMS1117-3.3",
                  270, 60, {"VI": "#+5V", "VO": "#+3V3", "GND": "#GND"},
                  "Package_TO_SOT_SMD:SOT-223-3_TabPin2"))
    P.append(Part("C5", "Device", "C", "10uF", 255, 85,
                  {"1": "#+5V", "2": "#GND"}, C_0805))
    P.append(Part("C6", "Device", "C", "10uF", 285, 85,
                  {"1": "#+3V3", "2": "#GND"}, C_0805))
    P.append(Part("FB1", "Device", "L_Ferrite", "600R@100MHz", 310, 60,
                  {"1": "#+3V3", "2": "#+3.3VA"},
                  "Inductor_SMD:L_0805_2012Metric"))
    c7 = Part("C7", "Device", "C", "10uF", 325, 60,
              {"1": "#+3.3VA", "2": "#GNDA"}, C_0805)
    P.append(c7)
    P.append(Part("C8", "Device", "C", "100nF", 337.5, 60,
                  {"1": "#+3.3VA", "2": "#GNDA"}, C_0603))
    P.append(Part("FB2", "Device", "L_Ferrite", "600R@100MHz", 310, 95,
                  {"1": "#GND", "2": "#GNDA"},
                  "Inductor_SMD:L_0805_2012Metric"))
    P.append(Part("R1", "Device", "R", "330R", 40, 100,
                  {"1": "#+3V3", "2": "PWR_LED_A"}, R_0603))
    P.append(Part("D4", "Device", "LED", "PWR", 60, 110,
                  {"2": "PWR_LED_A", "1": "#GND"},
                  "LED_SMD:LED_0603_1608Metric"))

    for p in P:
        sh.add(p)
        connect_part(sh, libdb, p, nc_rest=True)

    # PWR_FLAGs on nets driven only through passives/connectors
    tie_power(sh, "PWR_FLAG", *pin_pt(j1, "Connector_Generic", "Conn_01x02", "1"))
    tie_power(sh, "PWR_FLAG", *pin_pt(j1, "Connector_Generic", "Conn_01x02", "2"))
    tie_power(sh, "PWR_FLAG", *pin_pt(f1, "Device", "Fuse", "2"))          # VBUS_F
    tie_power(sh, "PWR_FLAG", *pin_pt(P[2], "Device", "D_Schottky", "1"))  # VBUS_PROT (D2 K)
    tie_power(sh, "PWR_FLAG", *pin_pt(P[8], "Device", "L", "2"))           # +5V (L1 out)
    tie_power(sh, "PWR_FLAG", *pin_pt(c7, "Device", "C", "1"))             # +3.3VA (C7 top)
    tie_power(sh, "PWR_FLAG", *pin_pt(c7, "Device", "C", "2"))             # GNDA (C7 bottom)

    sh.texts.append(("28V aircraft bus input: F1 fuse, D2 reverse-polarity series"
                     " Schottky, D1 transient clamp (DO-160 sect.16/17 needs an"
                     " upstream surge stage - see docs).", 30, 135, 2.0))
    sh.texts.append(("LM2576HV-5.0 (Vin max 60V) buck to 5V, AMS1117 LDO to 3.3V."
                     " FB1/FB2 split the analog codec supply +3.3VA / GNDA.",
                     30, 142, 2.0))
    return sh


def build_mcu():
    sh = Sheet("mcu.kicad_sch", "MCU - STM32H743 (RTP/Opus stack, ED-137 style)",
               PROJECT)
    P = []
    u3 = Part("U3", "MCU_ST_STM32H7", "STM32H743VITx", "STM32H743VIT6",
              210, 150, {
                  "VDD": "#+3V3", "VBAT": "#+3V3", "VDDA": "#+3V3",
                  "VREF+": "#+3V3", "VSS": "#GND", "VSSA": "#GND",
                  "48": "VCAP1", "73": "VCAP2",
                  "PH0": "OSC_IN", "PH1": "OSC_OUT",
                  "NRST": "NRST", "BOOT0": "BOOT0",
                  "PA1": "RMII_REF_CLK", "PA2": "RMII_MDIO", "PC1": "RMII_MDC",
                  "PA7": "RMII_CRS_DV", "PC4": "RMII_RXD0", "PC5": "RMII_RXD1",
                  "PB11": "RMII_TX_EN", "PB12": "RMII_TXD0", "PB13": "RMII_TXD1",
                  "PE10": "ETH_NRST",
                  "PE2": "SAI1_MCLK", "PE5": "SAI1_BCLK", "PE4": "SAI1_FS",
                  "PE6": "I2S_DIN", "PE3": "I2S_DOUT",
                  "PB6": "I2C1_SCL", "PB7": "I2C1_SDA",
                  "PA9": "UART1_TX", "PA10": "UART1_RX",
                  "PA13": "SWDIO", "PA14": "SWCLK",
                  "PD8": "PTT_VHF", "PD9": "PTT_HF",
                  "PD10": "COR_VHF", "PD11": "COR_HF",
                  "PD12": "LED_STAT1", "PD13": "LED_STAT2", "PD14": "LED_STAT3",
              },
              "Package_QFP:LQFP-100_14x14mm_P0.5mm")
    P.append(u3)
    P.append(Part("Y1", "Device", "Crystal", "25MHz", 120, 70,
                  {"1": "OSC_IN", "2": "OSC_OUT"},
                  "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"))
    P.append(Part("C10", "Device", "C", "18pF", 105, 85,
                  {"1": "OSC_IN", "2": "#GND"}, C_0603))
    P.append(Part("C11", "Device", "C", "18pF", 135, 85,
                  {"1": "OSC_OUT", "2": "#GND"}, C_0603))
    P.append(Part("C12", "Device", "C", "100nF", 100, 115,
                  {"1": "NRST", "2": "#GND"}, C_0603))
    P.append(Part("R2", "Device", "R", "10K", 100, 135,
                  {"1": "BOOT0", "2": "#GND"}, R_0603))
    P.append(Part("C13", "Device", "C", "2.2uF", 150, 240,
                  {"1": "VCAP1", "2": "#GND"}, C_0805))
    P.append(Part("C14", "Device", "C", "2.2uF", 165, 240,
                  {"1": "VCAP2", "2": "#GND"}, C_0805))
    x = 45
    for i in range(6):
        P.append(Part(f"C{15 + i}", "Device", "C", "100nF", x, 265,
                      {"1": "#+3V3", "2": "#GND"}, C_0603))
        x += 12.5
    P.append(Part("C21", "Device", "C", "4.7uF", x, 265,
                  {"1": "#+3V3", "2": "#GND"}, C_0805))
    P.append(Part("R3", "Device", "R", "4.7K", 330, 115,
                  {"1": "#+3V3", "2": "I2C1_SCL"}, R_0603))
    P.append(Part("R4", "Device", "R", "4.7K", 345, 115,
                  {"1": "#+3V3", "2": "I2C1_SDA"}, R_0603))
    P.append(Part("R5", "Device", "R", "10K", 330, 145,
                  {"1": "#+3V3", "2": "COR_VHF"}, R_0603))
    P.append(Part("R6", "Device", "R", "10K", 345, 145,
                  {"1": "#+3V3", "2": "COR_HF"}, R_0603))
    P.append(Part("J2", "Connector_Generic", "Conn_01x05", "SWD", 60, 120,
                  {"1": "#+3V3", "2": "SWDIO", "3": "SWCLK", "4": "#GND",
                   "5": "NRST"},
                  "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical"))
    P.append(Part("J3", "Connector_Generic", "Conn_01x04", "CONSOLE_UART",
                  60, 160, {"1": "UART1_TX", "2": "UART1_RX", "3": "#GND",
                            "4": "NC"},
                  "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"))
    for i, nm in enumerate(["1", "2", "3"]):
        P.append(Part(f"R{7 + i}", "Device", "R", "330R", 60 + 15 * i, 200,
                      {"1": f"LED_STAT{nm}", "2": f"LED{nm}_A"}, R_0603))
        P.append(Part(f"D{5 + i}", "Device", "LED", f"STAT{nm}",
                      60 + 15 * i, 225,
                      {"2": f"LED{nm}_A", "1": "#GND"},
                      "LED_SMD:LED_0603_1608Metric"))
    for p in P:
        sh.add(p)
        connect_part(sh, libdb, p, nc_rest=True)
    sh.texts.append(("STM32H743: lwIP + RTP/Opus (or G.711) firmware."
                     " SAI1 <-> TLV320AIC23B codec, RMII <-> LAN8742A PHY.",
                     30, 285, 2.0))
    sh.texts.append(("PD8/PD9 key the radio PTT optos; PD10/PD11 read COR/"
                     "squelch optos (10K pull-ups R5/R6).", 30, 291, 2.0))
    return sh


def build_ethernet():
    sh = Sheet("ethernet.kicad_sch", "Ethernet - LAN8742A RMII PHY + MagJack",
               PROJECT)
    P = []
    u4 = Part("U4", "Interface_Ethernet", "LAN8742A", "LAN8742A", 150, 110, {
        "VDD2A": "#+3V3", "VDD1A": "#+3V3", "VDDIO": "#+3V3",
        "VDDCR": "VDDCR", "VSS": "#GND",
        "XTAL1/CLKIN": "PHY_XTAL1", "XTAL2": "PHY_XTAL2",
        "TXD0": "RMII_TXD0", "TXD1": "RMII_TXD1", "TXEN": "RMII_TX_EN",
        "RXD0/MODE0": "RMII_RXD0", "RXD1/MODE1": "RMII_RXD1",
        "CRS_DV/MODE2": "RMII_CRS_DV", "MDIO": "RMII_MDIO", "MDC": "RMII_MDC",
        "~{RST}": "ETH_NRST", "~{INT}/REFCLKO": "RMII_REF_CLK",
        "RXER/PHYAD0": "NC",
        "LED1/REGOFF": "PHY_LED1", "LED2/~{INTSEL}": "PHY_LED2",
        "TXP": "ETH_TXP", "TXN": "ETH_TXN", "RXP": "ETH_RXP",
        "RXN": "ETH_RXN", "RBIAS": "RBIAS",
    }, "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm")
    P.append(u4)
    P.append(Part("Y2", "Device", "Crystal", "25MHz", 60, 50,
                  {"1": "PHY_XTAL1", "2": "PHY_XTAL2"},
                  "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"))
    P.append(Part("C22", "Device", "C", "18pF", 45, 65,
                  {"1": "PHY_XTAL1", "2": "#GND"}, C_0603))
    P.append(Part("C23", "Device", "C", "18pF", 75, 65,
                  {"1": "PHY_XTAL2", "2": "#GND"}, C_0603))
    c24 = Part("C24", "Device", "C", "1uF", 100, 40,
               {"1": "VDDCR", "2": "#GND"}, C_0603)
    P.append(c24)
    P.append(Part("R10", "Device", "R", "12.1K", 195, 135,
                  {"1": "RBIAS", "2": "#GND"}, R_0603))
    P.append(Part("R11", "Device", "R", "1.5K", 60, 105,
                  {"1": "#+3V3", "2": "RMII_MDIO"}, R_0603))
    # nINTSEL strap low -> REF_CLK Out mode (PHY generates 50MHz RMII clock)
    P.append(Part("R12", "Device", "R", "10K", 60, 130,
                  {"1": "PHY_LED2", "2": "#GND"}, R_0603))
    P.append(Part("R15", "Device", "R", "10K", 60, 155,
                  {"1": "#+3V3", "2": "ETH_NRST"}, R_0603))
    P.append(Part("C25", "Device", "C", "100nF", 75, 155,
                  {"1": "ETH_NRST", "2": "#GND"}, C_0603))
    for i, net in enumerate(["ETH_TXP", "ETH_TXN", "ETH_RXP", "ETH_RXN"]):
        P.append(Part(f"R{17 + i}", "Device", "R", "49.9R", 210 + 12.5 * i, 45,
                      {"1": "#+3V3", "2": net}, R_0603))
    # magjack centre taps: fed from +3V3 through a ferrite, decoupled
    P.append(Part("FB3", "Device", "L_Ferrite", "600R@100MHz", 200, 80,
                  {"1": "#+3V3", "2": "ETH_VCT"},
                  "Inductor_SMD:L_0805_2012Metric"))
    P.append(Part("C26", "Device", "C", "100nF", 215, 80,
                  {"1": "ETH_VCT", "2": "#GND"}, C_0603))
    P.append(Part("C27", "Device", "C", "10nF", 230, 80,
                  {"1": "ETH_VCT", "2": "#GND"}, C_0603))
    P.append(Part("R13", "Device", "R", "330R", 270, 55,
                  {"1": "#+3V3", "2": "LEDJ1_A"}, R_0603))
    P.append(Part("R14", "Device", "R", "330R", 282.5, 55,
                  {"1": "#+3V3", "2": "LEDJ2_A"}, R_0603))
    P.append(Part("J4", "Connector", "RJ45_Amphenol_RJMG1BD3B8K1ANR",
                  "RJ45_MagJack", 310, 110, {
                      "R1": "ETH_TXP", "R2": "ETH_TXN", "R3": "ETH_RXP",
                      "R6": "ETH_RXN", "R4": "ETH_VCT", "R5": "ETH_VCT",
                      "L1": "LEDJ1_A", "L2": "PHY_LED1",
                      "L4": "LEDJ2_A", "L3": "PHY_LED2",
                      "R8": "#GND", "SH": "#GND", "R7": "NC",
                  }, "Connector_RJ:RJ45_Amphenol_RJMG1BD3B8K1ANR"))
    P.append(Part("C40", "Device", "C", "100nF", 100, 55,
                  {"1": "#+3V3", "2": "#GND"}, C_0603))
    P.append(Part("C41", "Device", "C", "100nF", 112.5, 55,
                  {"1": "#+3V3", "2": "#GND"}, C_0603))
    for p in P:
        sh.add(p)
        connect_part(sh, libdb, p, nc_rest=True)
    # VDDCR is sourced by the PHY's internal core regulator
    tie_power(sh, "PWR_FLAG", *pin_pt(c24, "Device", "C", "1"))
    sh.texts.append(("LAN8742A strap: nINTSEL(LED2) pulled low = REF_CLK Out"
                     " mode - PHY sources the 50MHz RMII clock to PA1.",
                     30, 200, 2.0))
    sh.texts.append(("J4 has integrated magnetics; connects to the Starlink"
                     " router / aircraft IP LAN.", 30, 207, 2.0))
    return sh


def build_audio():
    sh = Sheet("audio.kicad_sch", "Audio Codec - TLV320AIC23B (L=VHF, R=HF)",
               PROJECT)
    P = []
    P.append(Part("U5", "Audio", "TLV320AIC23BPW", "TLV320AIC23BPW",
                  150, 110, {
                      "BVDD": "#+3V3", "DVDD": "#+3V3",
                      "HPVDD": "#+3.3VA", "AVDD": "#+3.3VA",
                      "DGND": "#GND", "AGND": "#GNDA", "HPGND": "#GNDA",
                      "BCLK": "SAI1_BCLK", "DIN": "I2S_DIN",
                      "LRCIN": "SAI1_FS", "DOUT": "I2S_DOUT",
                      "LRCOUT": "SAI1_FS",
                      "XTI/MCK": "SAI1_MCLK", "XTO": "NC", "CLKOUT": "NC",
                      "SCLK": "I2C1_SCL", "SDIN": "I2C1_SDA",
                      "~{CS}": "#GND", "MODE": "#GND",
                      "VMID": "VMID", "MICBIAS": "NC", "MICIN": "NC",
                      "LLINEIN": "VHF_RX_C", "RLINEIN": "HF_RX_C",
                      "LOUT": "VHF_TX_RAW", "ROUT": "HF_TX_RAW",
                      "LHPOUT": "NC", "RHPOUT": "NC",
                  }, "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm"))
    P.append(Part("C28", "Device", "C", "10uF", 220, 155,
                  {"1": "VMID", "2": "#GNDA"}, C_0805))
    P.append(Part("C29", "Device", "C", "100nF", 232.5, 155,
                  {"1": "VMID", "2": "#GNDA"}, C_0603))
    # RX coupling into line inputs (source: radio_if pads)
    P.append(Part("C30", "Device", "C", "1uF", 250, 60,
                  {"1": "VHF_RX_PAD", "2": "VHF_RX_C"}, C_0603))
    P.append(Part("R21", "Device", "R", "47K", 262.5, 60,
                  {"1": "VHF_RX_C", "2": "#GNDA"}, R_0603))
    P.append(Part("C31", "Device", "C", "1uF", 285, 60,
                  {"1": "HF_RX_PAD", "2": "HF_RX_C"}, C_0603))
    P.append(Part("R22", "Device", "R", "47K", 297.5, 60,
                  {"1": "HF_RX_C", "2": "#GNDA"}, R_0603))
    # TX AC coupling out to the radio_if transformers
    P.append(Part("C32", "Device", "C", "10uF", 250, 90,
                  {"1": "VHF_TX_RAW", "2": "VHF_TX_AC"}, C_0805))
    P.append(Part("C33", "Device", "C", "10uF", 285, 90,
                  {"1": "HF_TX_RAW", "2": "HF_TX_AC"}, C_0805))
    P.append(Part("C34", "Device", "C", "100nF", 60, 200,
                  {"1": "#+3V3", "2": "#GND"}, C_0603))
    P.append(Part("C35", "Device", "C", "100nF", 75, 200,
                  {"1": "#+3.3VA", "2": "#GNDA"}, C_0603))
    P.append(Part("C36", "Device", "C", "10uF", 90, 200,
                  {"1": "#+3.3VA", "2": "#GNDA"}, C_0805))
    for p in P:
        sh.add(p)
        connect_part(sh, libdb, p, nc_rest=True)
    sh.texts.append(("Stereo codec carries both radios: LEFT channel = VHF COM,"
                     " RIGHT channel = HF. I2C addr 0x1A (CS low), slave I2S,"
                     " MCLK from SAI1.", 30, 230, 2.0))
    sh.texts.append(("8kHz Fs is enough for airband AM voice (300-2500Hz);"
                     " 16kHz recommended with Opus.", 30, 237, 2.0))
    return sh


def build_radio_if():
    sh = Sheet("radio_if.kicad_sch",
               "Radio Interface - isolated audio/PTT/COR x2 (VHF + HF)",
               PROJECT)
    P = []
    P.append(Part("J5", "Connector", "DB25_Socket_MountingHoles", "TO_RADIOS",
                  50, 110, {
                      "1": "VHF_RX_HI", "14": "VHF_RX_LO",
                      "2": "VHF_MIC_HI", "15": "VHF_MIC_LO",
                      "3": "VHF_PTT_KEY", "16": "VHF_PTT_RET",
                      "4": "VHF_COR_HI", "17": "VHF_COR_LO",
                      "6": "HF_RX_HI", "19": "HF_RX_LO",
                      "7": "HF_MIC_HI", "20": "HF_MIC_LO",
                      "8": "HF_PTT_KEY", "21": "HF_PTT_RET",
                      "9": "HF_COR_HI", "22": "HF_COR_LO",
                      "13": "#GND", "25": "#GND", "SH": "#GND",
                  }, "Connector_Dsub:DSUB-25_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm"))

    def channel(pfx, x0, tref, uref, rref):
        # RX isolation transformer + pad
        P.append(Part(f"T{tref}", "Device", "Transformer_1P_1S", "600:600",
                      x0, 55, {"1": f"{pfx}_RX_HI", "2": f"{pfx}_RX_LO",
                               "4": f"{pfx}_RX_SEC", "3": "#GNDA"},
                      "Package_DIP:DIP-4_W10.16mm"))
        P.append(Part(f"R{rref}", "Device", "R", "10K", x0 + 22.5, 72.5,
                      {"1": f"{pfx}_RX_SEC", "2": f"{pfx}_RX_PAD"}, R_0603))
        P.append(Part(f"R{rref + 1}", "Device", "R", "10K", x0 + 35, 72.5,
                      {"1": f"{pfx}_RX_PAD", "2": "#GNDA"}, R_0603))
        # TX isolation transformer, driven from codec via series level R
        P.append(Part(f"R{rref + 2}", "Device", "R", "604R", x0 + 22.5, 92.5,
                      {"1": f"{pfx}_TX_AC", "2": f"{pfx}_TX_XFMR"}, R_0603))
        P.append(Part(f"T{tref + 1}", "Device", "Transformer_1P_1S", "600:600",
                      x0, 105, {"1": f"{pfx}_MIC_HI", "2": f"{pfx}_MIC_LO",
                                "4": f"{pfx}_TX_XFMR", "3": "#GNDA"},
                      "Package_DIP:DIP-4_W10.16mm"))
        # PTT opto: MCU GPIO -> R -> LED; output transistor keys radio PTT
        P.append(Part(f"R{rref + 3}", "Device", "R", "330R", x0 - 20, 140,
                      {"1": f"PTT_{pfx}", "2": f"PTT_{pfx}_A"}, R_0603))
        P.append(Part(f"U{uref}", "Isolator", "PC817", "PC817", x0, 140,
                      {"1": f"PTT_{pfx}_A", "2": "#GND",
                       "4": f"{pfx}_PTT_KEY", "3": f"{pfx}_PTT_RET"},
                      "Package_DIP:DIP-4_W7.62mm"))
        # COR/squelch opto: radio drives LED; transistor pulls COR_x low
        P.append(Part(f"R{rref + 4}", "Device", "R", "4.7K", x0 - 20, 175,
                      {"1": f"{pfx}_COR_HI", "2": f"{pfx}_COR_A"}, R_0603))
        P.append(Part(f"U{uref + 1}", "Isolator", "PC817", "PC817", x0, 175,
                      {"1": f"{pfx}_COR_A", "2": f"{pfx}_COR_LO",
                       "4": f"COR_{pfx}", "3": "#GND"},
                      "Package_DIP:DIP-4_W7.62mm"))

    channel("VHF", 150, 1, 6, 23)
    channel("HF", 260, 3, 8, 28)
    for p in P:
        sh.add(p)
        connect_part(sh, libdb, p, nc_rest=True)
    sh.texts.append(("Each radio channel is galvanically isolated: 600R audio"
                     " transformers (RX + TX) and PC817 optos for PTT key and"
                     " COR/squelch sense.", 30, 220, 2.0))
    sh.texts.append(("VHF ch: J5 pins 1/14 RX audio, 2/15 mic audio, 3/16 PTT,"
                     " 4/17 COR. HF ch: 6/19, 7/20, 8/21, 9/22. 13/25 chassis.",
                     30, 227, 2.0))
    sh.texts.append(("PTT keying: opto collector (KEY) pulls to radio ground"
                     " (RET) - max 50mA, 35V. Fit MOV/TVS across PTT lines for"
                     " HF coupler kick-back.", 30, 234, 2.0))
    return sh


def render_root(sheets):
    out = []
    out.append('(kicad_sch (version 20231120) (generator "atc_roip_gen")')
    out.append(f'  (uuid "{ROOT_UUID}")')
    out.append('  (paper "A3")')
    out.append('  (title_block')
    out.append('    (title "ATC Radio-over-IP Gateway - VHF/HF airborne RoIP")')
    out.append('    (company "ATC RoIP Gateway Project")')
    out.append('    (rev "A")')
    out.append('    (comment 1 "Pilot/remote op <-> RTP/IP (Starlink) <-> this'
               ' gateway <-> aircraft VHF+HF transceivers")')
    out.append('  )')
    out.append('  (lib_symbols)')
    x = 40
    for i, sh in enumerate(sheets):
        y = 60
        out.append(f'''  (sheet (at {fmt(x)} {fmt(y)}) (size 50 30) (fields_autoplaced yes)
    (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000))
    (uuid "{sh.uuid}")
    (property "Sheetname" "{sh.title.split(' - ')[0]}" (at {fmt(x)} {fmt(y - 2)} 0)
      (effects (font (size 1.27 1.27)) (justify left bottom)))
    (property "Sheetfile" "{sh.filename}" (at {fmt(x)} {fmt(y + 32)} 0)
      (effects (font (size 1.27 1.27)) (justify left top)))
    (instances (project "{PROJECT}" (path "/{ROOT_UUID}" (page "{i + 2}"))))
  )''')
        x += 70
    notes = [
        ("SIGNAL PATH:  ATC controller/remote pilot (RTP over IP via Starlink)"
         "  <->  RJ45 [ethernet]  <->  STM32H743 [mcu]  <->", 40, 130),
        ("TLV320AIC23B codec [audio]  <->  isolation transformers + PTT/COR"
         " optos [radio_if]  <->  VHF COM + HF transceivers via DB25", 40, 137),
        ("Power: 28VDC aircraft bus -> 5V buck -> 3.3V digital / 3.3VA analog"
         " [power]", 40, 148),
        ("NOTE: prototype / experimental hardware. Not a certified avionics"
         " article (no TSO/DO-160/DO-254 compliance claimed).", 40, 159),
    ]
    for t, tx, ty in notes:
        out.append(f'  (text "{t}" (exclude_from_sim no) (at {fmt(tx)} {fmt(ty)} 0)'
                   f' (effects (font (size 2 2)) (justify left bottom))'
                   f' (uuid "{new_uuid()}"))')
    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(')')
    return '\n'.join(out)


def write_pro():
    pro = {
        "board": {"design_settings": {}, "layer_presets": [], "viewports": []},
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
        "net_settings": {"classes": [], "meta": {"version": 3}},
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {
            "annotate_start_num": 0,
            "drawing": {"default_line_thickness": 6.0,
                        "default_text_size": 50.0,
                        "label_size_ratio": 0.375},
            "legacy_lib_dir": "", "legacy_lib_list": [],
            "meta": {"version": 1},
            "net_format_name": "",
            "page_layout_descr_file": "",
            "plot_directory": "",
            "spice_current_sheet_as_root": False,
            "spice_external_command": "spice \"%I\"",
            "spice_model_current_sheet_as_root": True,
            "spice_save_all_currents": False,
            "spice_save_all_voltages": False,
            "subpart_first_id": 65,
            "subpart_id_separator": 0,
        },
        "sheets": [],
        "text_variables": {},
    }
    with open(os.path.join(OUTDIR, f"{PROJECT}.kicad_pro"), "w",
              encoding="utf-8") as f:
        json.dump(pro, f, indent=2)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    sheets = [build_power(), build_mcu(), build_ethernet(), build_audio(),
              build_radio_if()]
    for i, sh in enumerate(sheets):
        text = render_sheet(sh, libdb, ROOT_UUID, sh.uuid, i + 2)
        with open(os.path.join(OUTDIR, sh.filename), "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote", sh.filename, f"({len(sh.parts)} parts,"
              f" {len(sh.labels)} labels, {len(sh.no_connects)} NCs)")
    with open(os.path.join(OUTDIR, f"{PROJECT}.kicad_sch"), "w",
              encoding="utf-8") as f:
        f.write(render_root(sheets))
    write_pro()
    print("wrote root +", f"{PROJECT}.kicad_pro")


if __name__ == "__main__":
    main()

