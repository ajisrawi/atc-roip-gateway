"""Splice the new PCB/BOM/verification sections into make_design_doc.py."""
import io
import re
import sys

sys.path.insert(0, r"C:\Users\ahmad\Documents\ATC ROIP\tools")
from _doc_tail import TAIL_INSERT

P = r"C:\Users\ahmad\Documents\ATC ROIP\tools\make_design_doc.py"
lines = io.open(P, encoding="utf-8").read().split("\n")

i_verif = next(i for i, l in enumerate(lines)
               if 'Verification' in l and 'st_h1' in l)
i_comp = next(i for i, l in enumerate(lines)
              if 'Compliance and regulatory' in l and 'st_h1' in l)

new_lines = (lines[:i_verif] + TAIL_INSERT.split("\n") + lines[i_comp:])
text = "\n".join(new_lines)

# renumber the remaining headings (loose match around the em-space)
text = re.sub(r'"8\s*\u2003?\s*Compliance and regulatory position"',
              '"10   Compliance and regulatory position"', text)
text = re.sub(r'"9\s*\u2003?\s*Next steps"', '"11   Next steps"', text)
text = text.replace(
    '"PCB layout: 4-layer (SIG / GND / PWR / SIG), short RMII, radio "',
    '"Order boards from the fab ZIP; assemble, bring up power, then SWD. "')
text = text.replace(
    '"isolation zone kept clear of digital return currents.",',
    '"",')
text = text.replace(
    'Connections are drawn netlist-style ',
    'Every pin carries a drawn wire stub with ')
text = text.replace(
    '"(global labels at pins); the netlist is the authoritative artifact "',
    '"its net label; the netlist is the authoritative artifact "')
text = text.replace('what the Section 7 checks validate',
                    'what the Section 9 checks validate')
io.open(P, "w", encoding="utf-8").write(text)
print("patched; markers at", i_verif, i_comp)
