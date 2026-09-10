"""Print copper occupancy near a point: map_area.py X_MM Y_MM RADIUS_MM"""
import math
import sys
import functools
import builtins

print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
board = pcbnew.LoadBoard(HW + r"\atc-roip-gateway.kicad_pcb")

cx, cy, rad = (float(a) for a in sys.argv[1:4])
c = pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy))
r = pcbnew.FromMM(rad)

def near(p):
    return math.hypot(p.x - c.x, p.y - c.y) < r

for fp in board.Footprints():
    for pad in fp.Pads():
        if near(pad.GetPosition()):
            p = pad.GetPosition()
            print(f"PAD {fp.GetReference()}.{pad.GetName():<3} "
                  f"net={pad.GetNetname():<14} "
                  f"({pcbnew.ToMM(p.x):.2f},{pcbnew.ToMM(p.y):.2f}) "
                  f"sz=({pcbnew.ToMM(pad.GetSize().x):.2f}x"
                  f"{pcbnew.ToMM(pad.GetSize().y):.2f})")
for t in board.GetTracks():
    cls = t.GetClass()
    if cls == 'PCB_VIA':
        if near(t.GetPosition()):
            p = t.GetPosition()
            print(f"VIA net={t.GetNetname():<14} "
                  f"({pcbnew.ToMM(p.x):.2f},{pcbnew.ToMM(p.y):.2f})")
    else:
        if near(t.GetStart()) or near(t.GetEnd()):
            s, e = t.GetStart(), t.GetEnd()
            lay = {0: 'F', 2: 'B', 4: 'In1', 6: 'In2'}.get(t.GetLayer(),
                                                           t.GetLayer())
            print(f"TRK {lay} net={t.GetNetname():<14} "
                  f"({pcbnew.ToMM(s.x):.2f},{pcbnew.ToMM(s.y):.2f})->"
                  f"({pcbnew.ToMM(e.x):.2f},{pcbnew.ToMM(e.y):.2f})")
