"""Pass 3: fix pass-2 collisions, then connect remaining orphan power pads
by (a) short F.Cu track to nearest same-net copper, else (b) escape + via
with proper multi-layer collision checks."""
import math
import re

import functools, builtins
print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"
RPT = HW + r"\drc.rpt"

VIA_DIA, VIA_DRILL, TRACK_W, CLR = 0.6, 0.3, 0.25, 0.2

import sys
PHASE = sys.argv[1] if len(sys.argv) > 1 else "connect"

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()

# ---- 1. remove items involved in clearance/hole_to_hole from pass 2 ------
text = open(RPT, encoding="utf-8").read()
bad_coords = []
for e in re.split(r'\n(?=\[)', text):
    if e.startswith('[clearance]') or e.startswith('[hole_to_hole]'):
        for m in re.finditer(r'@\((\d+\.\d+) mm, (\d+\.\d+) mm\): '
                             r'(Via|Track) \[(GND|\+3V3)\]', e):
            bad_coords.append((float(m.group(1)), float(m.group(2))))
if PHASE == "remove":
    removed = 0
    for t in list(board.GetTracks()):
        p = t.GetStart() if t.GetClass() == 'PCB_TRACK' else t.GetPosition()
        for bx, by in bad_coords:
            if (abs(pcbnew.ToMM(p.x) - bx) < 0.01 and
                    abs(pcbnew.ToMM(p.y) - by) < 0.01 and
                    t.GetNetname() in ("GND", "+3V3")):
                board.Remove(t)
                removed += 1
                break
    print("removed pass-2 offenders:", removed)
    pcbnew.SaveBoard(PCB, board)
    print("saved (remove phase)")
    sys.exit(0)

# ---- 2. rebuild item cache ----------------------------------------------
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
        hit_layer = False
        for layer in layers:
            if hasattr(it, "IsOnLayer") and not it.IsOnLayer(layer):
                continue
            hit_layer = True
            sh = it.GetEffectiveShape(layer)
            if sh.Collide(shape, pcbnew.FromMM(CLR)):
                return True
        if not hit_layer:
            continue
    return False


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


def add(item):
    board.Add(item)
    copper_items.append(item)


# ---- 3. connect orphans ---------------------------------------------------
TARGETS = []
for ref, pads in (("U3", None), ("U4", None), ("U5", None)):
    fp = board.FindFootprintByReference(ref)
    for pad in fp.Pads():
        nn = pad.GetNetname()
        if nn not in ("GND", "+3V3"):
            continue
        TARGETS.append((ref, pad))

fixed, failed = 0, []
for ref, pad in TARGETS:
    netname = pad.GetNetname()
    netcode = pad.GetNetCode()
    ppos = pad.GetPosition()
    # is this pad already touching a via/track? crude test: any same-net
    # track/via within (pad_half + 0.05mm)
    half = max(pad.GetSize().x, pad.GetSize().y) / 2
    touching = False
    for it in copper_items:
        if it is pad or it.GetNetCode() != netcode:
            continue
        if it.GetClass() not in ("PCB_TRACK", "PCB_VIA"):
            continue
        q = it.GetStart() if it.GetClass() == 'PCB_TRACK' else it.GetPosition()
        pts = [q]
        if it.GetClass() == 'PCB_TRACK':
            pts.append(it.GetEnd())
        for q2 in pts:
            if math.hypot(q2.x - ppos.x, q2.y - ppos.y) <= half:
                touching = True
                break
        if touching:
            break
    if touching:
        continue

    # (a) straight stub to nearest same-net track/via endpoint within 4 mm
    cands = []
    for it in copper_items:
        if it.GetNetCode() != netcode or it is pad:
            continue
        if it.GetClass() == 'PCB_VIA':
            pts = [it.GetPosition()]
        elif it.GetClass() == 'PCB_TRACK' and it.GetLayer() == pcbnew.F_Cu:
            pts = [it.GetStart(), it.GetEnd()]
        else:
            continue
        for q in pts:
            d = math.hypot(q.x - ppos.x, q.y - ppos.y)
            if d < pcbnew.FromMM(4.0):
                cands.append((d, q.x, q.y))
    cands.sort()
    placed = False
    for d, qx, qy in cands[:8]:
        seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(ppos.x, ppos.y),
                                   pcbnew.VECTOR2I(qx, qy),
                                   pcbnew.FromMM(TRACK_W))
        if collides(seg, (pcbnew.F_Cu,), netcode, (pad,)):
            continue
        add(make_track(ppos.x, ppos.y, qx, qy, netname))
        placed = True
        break

    # (b) escape outward + via
    if not placed:
        fp = board.FindFootprintByReference(ref)
        fpos = fp.GetPosition()
        dx, dy = ppos.x - fpos.x, ppos.y - fpos.y
        if abs(dx) > abs(dy):
            ux, uy = (1 if dx > 0 else -1), 0
        else:
            ux, uy = 0, (1 if dy > 0 else -1)
        for esc in (1.0, 1.5, 2.0, 2.8, 3.6, 4.5):
            e = pcbnew.FromMM(esc)
            vx, vy = ppos.x + ux * e, ppos.y + uy * e
            probe = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(vx), int(vy)),
                                        pcbnew.FromMM(VIA_DIA / 2))
            seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(ppos.x, ppos.y),
                                       pcbnew.VECTOR2I(int(vx), int(vy)),
                                       pcbnew.FromMM(TRACK_W))
            if collides(probe, (pcbnew.F_Cu, pcbnew.B_Cu), netcode, (pad,)):
                continue
            if collides(seg, (pcbnew.F_Cu,), netcode, (pad,)):
                continue
            add(make_track(ppos.x, ppos.y, vx, vy, netname))
            add(make_via(vx, vy, netname))
            placed = True
            break
    if placed:
        fixed += 1
    else:
        failed.append((ref, pad.GetName(), netname))

print("fixed:", fixed)
if failed:
    print("FAILED:", failed)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved")
