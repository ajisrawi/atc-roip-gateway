"""Directional fanout for fine-pitch IC power pads that pass 1 missed."""
import math

import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"

TARGETS = [
    ('U3', '10', 'GND'), ('U3', '100', '+3V3'), ('U3', '11', '+3V3'),
    ('U3', '19', 'GND'), ('U3', '26', 'GND'), ('U3', '27', '+3V3'),
    ('U3', '49', 'GND'), ('U3', '50', '+3V3'), ('U3', '6', '+3V3'),
    ('U3', '74', 'GND'), ('U3', '75', '+3V3'), ('U3', '99', 'GND'),
    ('U4', '1', '+3V3'), ('U4', '19', '+3V3'), ('U4', '25', 'GND'),
    ('U4', '9', '+3V3'), ('U5', '1', '+3V3'), ('U5', '28', 'GND'),
]

VIA_DIA, VIA_DRILL, TRACK_W, CLR = 0.6, 0.3, 0.25, 0.19

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()

copper_items = []
for fp in board.Footprints():
    for pad in fp.Pads():
        copper_items.append(pad)
for t in board.GetTracks():
    copper_items.append(t)


def collide_any(shape, netcode, skip):
    for it in copper_items:
        if it in skip:
            continue
        if hasattr(it, "GetNetCode") and it.GetNetCode() == netcode:
            continue
        sh = it.GetEffectiveShape(pcbnew.F_Cu)
        if sh.Collide(shape, pcbnew.FromMM(CLR)):
            return True
    return False


def add(board_item):
    board.Add(board_item)
    copper_items.append(board_item)


def make_via(x, y, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetWidth(pcbnew.FromMM(VIA_DIA))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(nets[netname])
    return v


def make_track(x1, y1, x2, y2, netname):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetLayer(pcbnew.F_Cu)
    t.SetWidth(pcbnew.FromMM(TRACK_W))
    t.SetNet(nets[netname])
    return t


fixed, failed = 0, []
for ref, pad_no, netname in TARGETS:
    fp = board.FindFootprintByReference(ref)
    pad = next((p for p in fp.Pads() if p.GetName() == pad_no), None)
    if pad is None:
        failed.append((ref, pad_no, "pad?"))
        continue
    ppos = pad.GetPosition()
    fpos = fp.GetPosition()
    netcode = pad.GetNetCode()
    dx, dy = ppos.x - fpos.x, ppos.y - fpos.y
    norm = math.hypot(dx, dy)
    placed = False
    if norm < pcbnew.FromMM(0.5):
        # centre pad (QFN EP): via-in-pad
        v = make_via(ppos.x, ppos.y, netname)
        add(v)
        placed = True
    else:
        # dominant axis escape, straight out from the body
        if abs(dx) > abs(dy):
            ux, uy = (1 if dx > 0 else -1), 0
        else:
            ux, uy = 0, (1 if dy > 0 else -1)
        for esc_mm in (1.0, 1.4, 1.8, 2.4, 3.2):
            e = pcbnew.FromMM(esc_mm)
            vx, vy = ppos.x + ux * e, ppos.y + uy * e
            probe = pcbnew.SHAPE_CIRCLE(
                pcbnew.VECTOR2I(int(vx), int(vy)),
                pcbnew.FromMM(VIA_DIA / 2))
            seg = pcbnew.SHAPE_SEGMENT(
                pcbnew.VECTOR2I(ppos.x, ppos.y),
                pcbnew.VECTOR2I(int(vx), int(vy)),
                pcbnew.FromMM(TRACK_W))
            if collide_any(probe, netcode, (pad,)):
                continue
            if collide_any(seg, netcode, (pad,)):
                continue
            add(make_track(ppos.x, ppos.y, vx, vy, netname))
            add(make_via(vx, vy, netname))
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
