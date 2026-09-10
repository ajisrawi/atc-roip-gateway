"""Reroute the RXD0 link through the y=138.15 channel; relocate one GND stub."""
import sys
import functools
import builtins

print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"
PHASE = sys.argv[1] if len(sys.argv) > 1 else "add"

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()


def MM(v):
    return pcbnew.FromMM(v)


def near(p, x, y, tol=0.05):
    return (abs(pcbnew.ToMM(p.x) - x) < tol and
            abs(pcbnew.ToMM(p.y) - y) < tol)


if PHASE == "remove":
    kill_tracks = [
        ("RMII_RXD0", (130.9, 136.9), (132.4, 138.79)),
        ("RMII_RXD0", (132.4, 138.79), (148.11, 138.79)),
        ("GND", (137.0, 137.18), (137.0, 137.78)),
        ("GND", (137.0, 137.78), (136.8, 136.97)),
    ]
    kill_vias = [("GND", (136.8, 136.97))]
    removed = 0
    for t in list(board.GetTracks()):
        nn = t.GetNetname()
        if t.GetClass() == 'PCB_TRACK':
            s, e = t.GetStart(), t.GetEnd()
            for (net, a, b) in kill_tracks:
                if nn == net and ((near(s, *a) and near(e, *b)) or
                                  (near(s, *b) and near(e, *a))):
                    board.Remove(t)
                    removed += 1
                    break
        else:
            p = t.GetPosition()
            for (net, a) in kill_vias:
                if nn == net and near(p, *a):
                    board.Remove(t)
                    removed += 1
                    break
    print("removed:", removed)
    pcbnew.SaveBoard(PCB, board)
    sys.exit(0)


def track(x1, y1, x2, y2, netname, layer=pcbnew.F_Cu, w=0.2):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    t.SetLayer(layer)
    t.SetWidth(MM(w))
    t.SetNet(nets[netname])
    board.Add(t)


track(130.9, 136.9, 132.3, 138.15, "RMII_RXD0")
track(132.3, 138.15, 138.3, 138.15, "RMII_RXD0")
track(138.3, 138.15, 138.3, 138.79, "RMII_RXD0")
track(138.3, 138.79, 148.11, 138.79, "RMII_RXD0")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("added")
