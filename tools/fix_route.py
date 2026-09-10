"""Manual completion: route RMII_RXD0 and add plane-stitching vias."""
import pcbnew

PCB = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway\atc-roip-gateway.kicad_pcb"

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()


def net(name):
    return nets[name]


def add_track(x1, y1, x2, y2, layer, netname, width=0.25):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    t.SetLayer(layer)
    t.SetWidth(pcbnew.FromMM(width))
    t.SetNet(net(netname))
    board.Add(t)


def add_via(x, y, netname, drill=0.3, size=0.6):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(pcbnew.FromMM(drill))
    v.SetWidth(pcbnew.FromMM(size))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net(netname))
    board.Add(v)


# ---- RMII_RXD0: U4 pad8 (128.25,133.9375) -> U3 pad32 (154.0,137.675) ----
add_track(128.25, 133.9375, 128.25, 136.2, pcbnew.F_Cu, "RMII_RXD0")
add_via(128.25, 136.2, "RMII_RXD0")
add_track(128.25, 136.2, 151.3, 136.2, pcbnew.B_Cu, "RMII_RXD0")
add_track(151.3, 136.2, 152.775, 137.675, pcbnew.B_Cu, "RMII_RXD0")
add_via(152.775, 137.675, "RMII_RXD0")
add_track(152.775, 137.675, 154.0, 137.675, pcbnew.F_Cu, "RMII_RXD0")

# ---- plane stitching vias -------------------------------------------------
add_via(129.0, 132.0, "GND")            # U4 exposed pad centre
add_via(203.05, 174.6625, "GND")        # C5 pad 2
add_via(127.0625, 130.75, "+3V3")       # U4 pad 1 (via-in-pad, prototype ok)
add_via(151.5, 138.983, "+3V3")         # orphan +3V3 stub end
add_via(165.4625, 119.2375, "+3V3")     # orphan +3V3 stub end

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("done")
