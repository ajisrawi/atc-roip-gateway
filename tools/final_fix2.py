"""Correct the last conflicts: RXD0 rail join, U3.27 via-in-pad,
U3.74 nudge, duplicate via removal."""
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


def near(p, x, y, tol=0.03):
    return (abs(pcbnew.ToMM(p.x) - x) < tol and
            abs(pcbnew.ToMM(p.y) - y) < tol)


if PHASE == "remove":
    kill_tracks = [
        ("RMII_RXD0", (131.87, 138.0), (147.33, 138.0)),
        ("RMII_RXD0", (147.33, 138.0), (148.11, 138.79)),
        ("RMII_RXD0", (130.9, 136.9), (131.87, 138.0)),
        ("+3V3", (151.5, 137.675), (151.6, 139.3)),
        ("GND", (164.675, 124.5), (165.55, 124.5)),
    ]
    kill_vias = [
        ("+3V3", (151.6, 139.3)),
        ("GND", (165.55, 124.5)),
        ("GND", (182.6625, 132.125)),
        ("+3V3", (149.125, 133.8)),
    ]
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


def via(x, y, netname, dia=0.45, drill=0.2):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(MM(drill))
    v.SetWidth(MM(dia))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(nets[netname])
    board.Add(v)


# RXD0: from the B->F via straight onto the router's y=138.79 rail
track(130.9, 136.9, 132.4, 138.79, "RMII_RXD0")
track(132.4, 138.79, 148.11, 138.79, "RMII_RXD0")

# U3.27 (+3V3): small via directly in the pad's lower half
via(151.5, 138.2, "+3V3", dia=0.4, drill=0.2)

# U3.74 (GND): via nudged clear of the SWDIO B.Cu wall
via(165.535, 124.5, "GND", dia=0.4, drill=0.2)
track(164.675, 124.5, 165.535, 124.5, "GND")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("added")
