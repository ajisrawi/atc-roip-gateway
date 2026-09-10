"""Pass 4: L-shaped escape search for the last walled-in power pads."""
import math
import sys
import functools
import builtins

print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"

TARGETS = [
    ('U3', '10', 'GND'), ('U3', '11', '+3V3'), ('U3', '26', 'GND'),
    ('U3', '27', '+3V3'), ('U3', '49', 'GND'), ('U3', '74', 'GND'),
    ('U3', '75', '+3V3'), ('U4', '1', '+3V3'), ('U4', '9', '+3V3'),
    ('U5', '1', '+3V3'), ('U5', '28', 'GND'),
]

VIA_DIA, VIA_DRILL, TRACK_W, CLR = 0.6, 0.3, 0.2, 0.2

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()

copper_items = []
for fp in board.Footprints():
    for pad in fp.Pads():
        copper_items.append(pad)
for t in board.GetTracks():
    copper_items.append(t)


def collides(shape, layers, netcode, skip):
    for it in copper_items:
        if it in skip:
            continue
        if hasattr(it, "GetNetCode") and it.GetNetCode() == netcode:
            continue
        for layer in layers:
            if hasattr(it, "IsOnLayer") and not it.IsOnLayer(layer):
                continue
            sh = it.GetEffectiveShape(layer)
            if sh.Collide(shape, pcbnew.FromMM(CLR)):
                return True
            break
    return False


def seg_shape(x1, y1, x2, y2, w=TRACK_W):
    return pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(int(x1), int(y1)),
                                pcbnew.VECTOR2I(int(x2), int(y2)),
                                pcbnew.FromMM(w))


def circle_shape(x, y, r_mm):
    return pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)),
                               pcbnew.FromMM(r_mm))


def add_track(x1, y1, x2, y2, netname):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetLayer(pcbnew.F_Cu)
    t.SetWidth(pcbnew.FromMM(TRACK_W))
    t.SetNet(nets[netname])
    board.Add(t)
    copper_items.append(t)


def add_via(x, y, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetWidth(pcbnew.FromMM(VIA_DIA))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(nets[netname])
    board.Add(v)
    copper_items.append(v)


fixed, failed = 0, []
for ref, pad_no, netname in TARGETS:
    fp = board.FindFootprintByReference(ref)
    pad = next((p for p in fp.Pads() if p.GetName() == pad_no), None)
    ppos = pad.GetPosition()
    fpos = fp.GetPosition()
    netcode = pad.GetNetCode()
    dx, dy = ppos.x - fpos.x, ppos.y - fpos.y
    if abs(dx) > abs(dy):
        ux, uy = (1 if dx > 0 else -1), 0
    else:
        ux, uy = 0, (1 if dy > 0 else -1)
    # perpendicular unit
    px, py = -uy, ux
    placed = False
    for out_mm in (0.8, 1.0, 1.3, 1.7, 2.2):
        if placed:
            break
        o = pcbnew.FromMM(out_mm)
        wx, wy = ppos.x + ux * o, ppos.y + uy * o
        if collides(seg_shape(ppos.x, ppos.y, wx, wy), (pcbnew.F_Cu,),
                    netcode, (pad,)):
            continue
        # try via right at the waypoint first, then slide sideways
        for side_mm in (0.0, 0.5, -0.5, 1.0, -1.0, 1.6, -1.6, 2.4, -2.4,
                        3.4, -3.4):
            s = pcbnew.FromMM(side_mm)
            vx, vy = wx + px * s, wy + py * s
            if side_mm != 0.0:
                if collides(seg_shape(wx, wy, vx, vy), (pcbnew.F_Cu,),
                            netcode, (pad,)):
                    continue
            if collides(circle_shape(vx, vy, VIA_DIA / 2),
                        (pcbnew.F_Cu, pcbnew.B_Cu), netcode, (pad,)):
                continue
            add_track(ppos.x, ppos.y, wx, wy, netname)
            if side_mm != 0.0:
                add_track(wx, wy, vx, vy, netname)
            add_via(vx, vy, netname)
            placed = True
            break
    if placed:
        fixed += 1
    else:
        failed.append((ref, pad_no, netname))

print("fixed:", fixed)
if failed:
    print("FAILED:", failed)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved")
