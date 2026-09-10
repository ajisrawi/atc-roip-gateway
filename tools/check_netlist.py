"""Verify key nets in the exported netlist."""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'netlist.net'
text = open(path, encoding='utf-8').read()

nets = {}
for m in re.finditer(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)', text):
    start = m.start()
    depth = 0
    j = start
    while j < len(text):
        c = text[j]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                break
        j += 1
    block = text[start:j + 1]
    nodes = re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', block)
    nets[m.group(1)] = sorted(f"{r}.{p}" for r, p in nodes
                              if not r.startswith('#'))

checks = {
    "RMII_TXD0": {"U3.51", "U4.17"},
    "RMII_REF_CLK": {"U3.23", "U4.14"},
    "SAI1_FS": {"U3.3", "U5.5", "U5.7"},
    "I2C1_SDA": {"U3.93", "U5.23", "R4.2"},
    "PTT_VHF": {"U3.55", "R26.1"},
    "VHF_PTT_KEY": {"U6.4", "J5.3"},
    "COR_HF": {"U3.58", "R6.2", "U9.4"},
    "VHF_RX_PAD": {"R23.2", "R24.1", "C30.1"},
    "ETH_TXP": {"U4.21", "J4.R1", "R17.2"},
    "VMID": {"U5.16", "C28.1", "C29.1"},
    "VBUS_PROT": {"D2.1", "D1.1", "C1.1", "C2.1", "U1.1"},
    "SAI1_MCLK": {"U3.1", "U5.25"},
    "I2S_DOUT": {"U3.2", "U5.6"},
    "UART1_TX": {"U3.68", "J3.1"},
}
ok = True
for net, want in checks.items():
    found = None
    for k, v in nets.items():
        if k == net or k.endswith('/' + net):
            found = (k, set(v))
            break
    if not found:
        print(f"FAIL {net}: net not found")
        ok = False
        continue
    k, have = found
    if want <= have:
        print(f"OK   {net}: {sorted(have)}")
    else:
        print(f"FAIL {net}: want {sorted(want)}, have {sorted(have)}")
        ok = False

for rail in ("+3V3", "GND", "GNDA", "+3.3VA", "+5V"):
    for k, v in nets.items():
        if k == rail:
            print(f"rail {rail}: {len(v)} pins")
print("total nets:", len(nets))
sys.exit(0 if ok else 1)
