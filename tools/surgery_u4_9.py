"""Free U4.9 (VDDIO): move the blocking RMII_RXD0 trace to B.Cu, then
fan out U4.9 through the freed corridor."""
import functools
import builtins

print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"

import sys
PHASE = sys.argv[1] if len(sys.argv) > 1 else "add"

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()


def MM(v):
    return pcbnew.FromMM(v)


def near(p, x, y, tol=0.03):
    return (abs(pcbnew.ToMM(p.x) - x) < tol and
            abs(pcbnew.ToMM(p.y) - y) < tol)


if PHASE == "remove":
    removed = 0
    for t in list(board.GetTracks()):
        if t.GetClass() != 'PCB_TRACK' or t.GetNetname() != 'RMII_RXD0':
            continue
        s, e = t.GetStart(), t.GetEnd()
        if (near(s, 128.25, 133.9375) and near(e, 128.25, 134.38)) or \
           (near(s, 128.25, 134.38) and near(e, 128.25, 133.9375)):
            board.Remove(t)
            removed += 1
        elif (near(s, 128.25, 134.38) and near(e, 131.87, 138.0)) or \
             (near(s, 131.87, 138.0) and near(e, 128.25, 134.38)):
            board.Remove(t)
            removed += 1
    print("removed RXD0 segments:", removed)
    pcbnew.SaveBoard(PCB, board)
    sys.exit(0)


def track(x1, y1, x2, y2, layer, netname, w=0.2):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    t.SetLayer(layer)
    t.SetWidth(MM(w))
    t.SetNet(nets[netname])
    board.Add(t)


def via(x, y, netname, dia=0.45, drill=0.2):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(MM(drill))
    v.SetWidth(MM(dia))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(nets[netname])
    board.Add(v)


F, B = pcbnew.F_Cu, pcbnew.B_Cu
# 2. RXD0 re-route: short F stub, dive to B, resurface at the old junction
track(128.25, 133.9375, 128.25, 134.6, F, "RMII_RXD0")
track(128.25, 134.6, 128.35, 135.9, F, "RMII_RXD0")
via(128.35, 135.9, "RMII_RXD0")
track(128.35, 135.9, 131.87, 137.6, B, "RMII_RXD0")
track(131.87, 137.6, 131.87, 138.0, B, "RMII_RXD0")
via(131.87, 138.0, "RMII_RXD0")

# 3. U4.9 VDDIO fanout through the freed corridor
track(128.75, 133.9375, 128.85, 134.9, F, "+3V3")
via(128.85, 134.9, "+3V3")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("surgery done")
