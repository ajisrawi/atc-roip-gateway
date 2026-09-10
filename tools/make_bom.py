"""Generate the complete BOM (CSV) from the exported KiCad netlist."""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NETLIST = os.path.join(ROOT, "hardware", "atc-roip-gateway", "netlist.net")
OUT_CSV = os.path.join(ROOT, "docs", "BOM.csv")

# MPN map keyed by (value, footprint-tail) or by ref prefix fallback.
# fields: manufacturer, MPN, description, note
MPN = {
    ("STM32H743VIT6", "LQFP-100"): (
        "STMicroelectronics", "STM32H743VIT6",
        "MCU Cortex-M7 480MHz, 2MB flash, ETH MAC, SAI, LQFP-100", ""),
    ("LAN8742A", "QFN-24"): (
        "Microchip", "LAN8742A-CZ-TR",
        "10/100 Ethernet PHY, RMII, QFN-24", ""),
    ("TLV320AIC23BPW", "TSSOP-28"): (
        "Texas Instruments", "TLV320AIC23BPWR",
        "Stereo audio codec, I2S, TSSOP-28", ""),
    ("LM2576HVS-5.0", "TO-263"): (
        "Texas Instruments", "LM2576HVS-5.0/NOPB",
        "Buck regulator 5V 3A, Vin max 60V, TO-263-5", ""),
    ("AMS1117-3.3", "SOT-223"): (
        "AMS / UMW", "AMS1117-3.3",
        "LDO 3.3V 1A, SOT-223", ""),
    ("PC817", "DIP-4"): (
        "Sharp", "PC817X2NSZ9F",
        "Optocoupler, transistor output, 5kV, DIP-4", ""),
    ("SMCJ33A", "D_SMC"): (
        "Littelfuse", "SMCJ33A",
        "TVS diode 33V standoff, 1500W, SMC", ""),
    ("SS54", "D_SMA"): (
        "Vishay / MDD", "SS54",
        "Schottky diode 40V 5A, SMA", ""),
    ("25MHz", "3225"): (
        "Abracon", "ABM3-25.000MHZ-D2Y-T",
        "Crystal 25MHz, 18pF CL, 3.2x2.5mm SMD", ""),
    ("600:600", "DIP-4"): (
        "Triad Magnetics", "SP-66 (or Tamura TTC-108)",
        "Audio transformer 600:600 ohm, isolation",
        "Footprint is DIP-4 placeholder - verify against chosen part"),
    ("RJ45_MagJack", "RJMG1BD3B8K1ANR"): (
        "Amphenol", "RJMG1BD3B8K1ANR",
        "RJ45 jack with integrated 10/100 magnetics + LEDs", ""),
    ("TO_RADIOS", "DSUB-25"): (
        "NorComp / Amphenol", "182-025-113R531 (female) or L717SDB25P",
        "DB25 D-sub connector, horizontal PCB mount",
        "Choose male/female per aircraft harness; footprint is male-pins"),
    ("28VDC_BUS_IN", "TerminalBlock"): (
        "Phoenix Contact", "1715022 (MKDS 1,5/2-5,08)",
        "2-pos screw terminal block, 5.08mm", ""),
    ("SWD", "1x05"): (
        "generic", "PinHeader 1x05 2.54mm",
        "SWD debug header", ""),
    ("CONSOLE_UART", "1x04"): (
        "generic", "PinHeader 1x04 2.54mm",
        "Console UART header", ""),
    ("100uH/3A", "L_12x12"): (
        "Bourns", "SRP1265A-101M",
        "Power inductor 100uH 3A shielded", ""),
    ("600R@100MHz", "L_0805"): (
        "Murata", "BLM21PG600SN1D",
        "Ferrite bead 600R @ 100MHz, 0805", ""),
    ("1A", "Fuse_1206"): (
        "Littelfuse", "0451001.MRL",
        "Fuse 1A fast, 1206", ""),
    ("100uF/63V", "CP_Elec_8x10"): (
        "Panasonic", "EEE-FK1J101P",
        "Aluminum electrolytic 100uF 63V, SMD 8x10.2", ""),
    ("470uF/16V", "CP_Elec_8x10"): (
        "Panasonic", "EEE-FK1C471P",
        "Aluminum electrolytic 470uF 16V, SMD 8x10.2", ""),
    ("PWR", "LED_0603"): (
        "Everlight", "19-217/GHC-YR1S2/3T",
        "LED green 0603", ""),
    ("STAT1", "LED_0603"): (
        "Everlight", "19-217/GHC-YR1S2/3T", "LED green 0603", ""),
    ("STAT2", "LED_0603"): (
        "Everlight", "19-217/GHC-YR1S2/3T", "LED green 0603", ""),
    ("STAT3", "LED_0603"): (
        "Everlight", "19-217/GHC-YR1S2/3T", "LED green 0603", ""),
}

GENERIC = {
    ("R", "R_0603"): ("Yageo", "RC0603FR-07{val}L",
                      "Resistor {val} 1% 0603", ""),
    ("C", "C_0603"): ("Samsung", "CL10 series",
                      "Capacitor {val} X7R 0603 (NP0 for 18pF)", ""),
    ("C", "C_0805"): ("Samsung", "CL21 series",
                      "Capacitor {val} X7R/X5R 0805", ""),
}


def parse_components(path):
    text = open(path, encoding="utf-8").read()
    comps = []
    for m in re.finditer(
            r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\)\s+'
            r'(?:\(footprint "([^"]*)"\))?', text):
        comps.append((m.group(1), m.group(2), m.group(3) or ""))
    return comps


def match_mpn(ref, value, footprint):
    for (val, fptail), info in MPN.items():
        if value == val and fptail in footprint:
            return info
    prefix = re.match(r'[A-Za-z]+', ref).group(0)
    kind = ("R" if prefix == "R" else
            "C" if prefix == "C" else None)
    if kind:
        for (k, fptail), info in GENERIC.items():
            if k == kind and fptail in footprint:
                mfr, mpn, desc, note = info
                return (mfr, mpn.replace("{val}", value),
                        desc.replace("{val}", value), note)
    return ("", "TBD", value, "no MPN assigned")


def main():
    comps = parse_components(NETLIST)
    groups = {}
    for ref, value, fp in comps:
        if ref.startswith("#"):
            continue
        info = match_mpn(ref, value, fp)
        key = (value, fp, info[1])
        groups.setdefault(key, {"refs": [], "info": info,
                                "value": value, "fp": fp})["refs"].append(ref)

    def refkey(r):
        m = re.match(r'([A-Za-z]+)(\d+)', r)
        return (m.group(1), int(m.group(2)))

    rows = []
    for key, g in groups.items():
        refs = sorted(g["refs"], key=refkey)
        mfr, mpn, desc, note = g["info"]
        fp_short = g["fp"].split(":")[-1] if g["fp"] else ""
        rows.append([", ".join(refs), len(refs), g["value"], desc, mfr, mpn,
                     fp_short, note])
    rows.sort(key=lambda r: refkey(r[0].split(",")[0]))

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["References", "Qty", "Value", "Description",
                    "Manufacturer", "MPN", "Footprint", "Notes"])
        w.writerows(rows)
    total = sum(r[1] for r in rows)
    print(f"BOM: {len(rows)} line items, {total} components -> {OUT_CSV}")
    tbd = [r for r in rows if r[5] == "TBD"]
    for r in tbd:
        print("  TBD:", r[0], r[2], r[6])


if __name__ == "__main__":
    main()
