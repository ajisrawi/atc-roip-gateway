"""Add collision-checked fanout (stitching) vias for orphan plane-net pads.

Parses the DRC report's unconnected_items entries, finds SMD pads on the
plane nets, and drops a via + short F.Cu stub next to each in the first
collision-free spot.
"""
import math
import re
import sys

import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"
RPT = HW + r"\drc.rpt"

PLANE_NETS = {"GND": "GND", "+3V3": "+3V3"}
VIA_DIA, VIA_DRILL, TRACK_W, CLR = 0.6, 0.3, 0.3, 0.25

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()

# ---- orphan pads from DRC report ----------------------------------------
text = open(RPT, encoding="utf-8").read()
orphans = set()
for e in re.split(r'\n(?=\[)', text):
    if not e.startswith('[unconnected_items]'):
        continue
    for m in re.finditer(r'Pad (\S+) \[([^\]]+)\] of (\S+) on F\.Cu', e):
        pad_no, netname, ref = m.groups()
        if netname in PLANE_NETS:
            orphans.add((ref, pad_no, netname))
print("orphan plane pads:", len(orphans))

# ---- collision helpers ---------------------------------------------------
copper_items = []
for fp in board.Footprints():
    for pad in fp.Pads():
        copper_items.append(pad)
for t in board.GetTracks():
    copper_items.append(t)


def spot_free(x_iu, y_iu, radius_iu, netcode, skip=()):
    probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(x_iu, y_iu), radius_iu)
    for it in copper_items:
        if it in skip:
            continue
        if hasattr(it, "GetNetCode") and it.GetNetCode() == netcode:
            continue                      # same net may touch
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu,
                      pcbnew.In2_Cu):
            if hasattr(it, "IsOnLayer") and not it.IsOnLayer(layer):
                continue
            sh = it.GetEffectiveShape(layer)
            if sh.Collide(probe, pcbnew.FromMM(CLR)):
                return False
            break                          # shape identical across layers
    return True


def seg_free(x1, y1, x2, y2, netcode, skip=()):
    seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(x1, y1),
                               pcbnew.VECTOR2I(x2, y2),
                               pcbnew.FromMM(TRACK_W))
    for it in copper_items:
        if it in skip:
            continue
        if hasattr(it, "GetNetCode") and it.GetNetCode() == netcode:
            continue
        if hasattr(it, "IsOnLayer") and not it.IsOnLayer(pcbnew.F_Cu):
            continue
        sh = it.GetEffectiveShape(pcbnew.F_Cu)
        if sh.Collide(seg, pcbnew.FromMM(CLR)):
            return False
    return True


def add_via(x_iu, y_iu, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(x_iu, y_iu))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetWidth(pcbnew.FromMM(VIA_DIA))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(nets[netname])
    board.Add(v)
    copper_items.append(v)
    return v


def add_track(x1, y1, x2, y2, netname):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(x1, y1))
    t.SetEnd(pcbnew.VECTOR2I(x2, y2))
    t.SetLayer(pcbnew.F_Cu)
    t.SetWidth(pcbnew.FromMM(TRACK_W))
    t.SetNet(nets[netname])
    board.Add(t)
    copper_items.append(t)
    return t


fixed, failed = 0, []
for ref, pad_no, netname in sorted(orphans):
    fp = board.FindFootprintByReference(ref)
    pad = None
    for p in fp.Pads():
        if p.GetName() == pad_no:
            pad = p
            break
    if pad is None:
        failed.append((ref, pad_no, "pad?"))
        continue
    pos = pad.GetPosition()
    sz = pad.GetSize()
    half = max(sz.x, sz.y) / 2
    netcode = pad.GetNetCode()
    placed = False
    for dist_mm in (0.9, 1.2, 1.6, 2.2, 3.0):
        d_iu = half + pcbnew.FromMM(dist_mm)
        for k in range(16):
            a = 2 * math.pi * k / 16
            vx = int(pos.x + d_iu * math.cos(a))
            vy = int(pos.y + d_iu * math.sin(a))
            if not spot_free(vx, vy, pcbnew.FromMM(VIA_DIA / 2), netcode,
                             skip=(pad,)):
                continue
            if not seg_free(pos.x, pos.y, vx, vy, netcode, skip=(pad,)):
                continue
            add_track(pos.x, pos.y, vx, vy, netname)
            add_via(vx, vy, netname)
            placed = True
            break
        if placed:
            break
    if placed:
        fixed += 1
    else:
        failed.append((ref, pad_no, netname))

print("fanout vias added:", fixed)
if failed:
    print("FAILED:", failed)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved")
