"""Final three connections: U3.27, U3.74, RXD0 continuation."""
import functools
import builtins

print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()
ds = board.GetDesignSettings()
ds.m_ViasMinSize = pcbnew.FromMM(0.4)


def MM(v):
    return pcbnew.FromMM(v)


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


# U3.27 (+3V3): escape below the bottom pad row
track(151.5, 137.675, 151.6, 139.3, "+3V3")
via(151.6, 139.3, "+3V3")

# U3.74 (GND): 0.4mm via exactly between pad rows (0.15mm clearance)
track(164.675, 124.5, 165.55, 124.5, "GND")
via(165.55, 124.5, "GND", dia=0.4, drill=0.2)

# RXD0: continue from the dodge to the router's remaining segment
track(131.87, 138.0, 147.3257, 138.0, "RMII_RXD0")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("final fixes added")
