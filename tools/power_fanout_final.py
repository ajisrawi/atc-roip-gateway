"""Clean-slate power fanout.

Phase 'wipe': remove ALL GND/+3V3 tracks+vias (all were script-added; the
router only routed signal nets) and the RXD0 dive segments.
Phase 'add': re-add the RXD0 B.Cu dodge (verified against ETH_NRST), the
U4.9 VDDIO fanout, then a deterministic collision-checked stub+via fanout
for every GND/+3V3 SMD pad and regulator tab on the board.
"""
import math
import sys
import functools
import builtins

print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"

VIA_DIA, VIA_DRILL, TRACK_W, CLR = 0.45, 0.2, 0.22, 0.155
F, B = None, None  # set after import binding

PHASE = sys.argv[1] if len(sys.argv) > 1 else "add"

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def MM(v):
    return pcbnew.FromMM(v)


if PHASE == "wipe":
    removed = 0
    for t in list(board.GetTracks()):
        nn = t.GetNetname()
        if nn in ("GND", "+3V3"):
            board.Remove(t)
            removed += 1
        elif nn == "RMII_RXD0":
            # remove the manual dive attempt (keep router segments near U3)
            pts = []
            if t.GetClass() == 'PCB_TRACK':
                pts = [t.GetStart(), t.GetEnd()]
            else:
                pts = [t.GetPosition()]
            for p in pts:
                x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
                if 127.5 < x < 132.5 and 133.5 < y < 138.5:
                    board.Remove(t)
                    removed += 1
                    break
    print("wiped:", removed)
    pcbnew.SaveBoard(PCB, board)
    sys.exit(0)

# ---------------------------------------------------------------- add phase
all_items = []
for fp in board.Footprints():
    for pad in fp.Pads():
        all_items.append(pad)
for t in board.GetTracks():
    all_items.append(t)


def item_anchor(it):
    if it.GetClass() == 'PCB_TRACK':
        s, e = it.GetStart(), it.GetEnd()
        return ((s.x + e.x) // 2, (s.y + e.y) // 2,
                math.hypot(e.x - s.x, e.y - s.y) / 2)
    p = it.GetPosition()
    return (p.x, p.y, MM(2))


def local_items(cx, cy, r_iu, netcode):
    out = []
    for it in all_items:
        if it.GetNetCode() == netcode:
            continue
        ax, ay, extra = item_anchor(it)
        if math.hypot(ax - cx, ay - cy) < r_iu + extra + MM(1.5):
            out.append(it)
    return out


def collide(items, shape, layers):
    for it in items:
        for layer in layers:
            if hasattr(it, "IsOnLayer") and not it.IsOnLayer(layer):
                continue
            if it.GetEffectiveShape(layer).Collide(shape, MM(CLR)):
                return True
            break
    return False


def seg_sh(x1, y1, x2, y2, w=TRACK_W):
    return pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(int(x1), int(y1)),
                                pcbnew.VECTOR2I(int(x2), int(y2)), MM(w))


def circ_sh(x, y):
    return pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)),
                               MM(VIA_DIA / 2))


def add_track(x1, y1, x2, y2, netname, layer=None, w=TRACK_W):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetLayer(layer if layer is not None else F)
    t.SetWidth(MM(w))
    t.SetNet(nets[netname])
    board.Add(t)
    all_items.append(t)


def add_via(x, y, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(MM(VIA_DRILL))
    v.SetWidth(MM(VIA_DIA))
    v.SetLayerPair(F, B)
    v.SetNet(nets[netname])
    board.Add(v)
    all_items.append(v)


# 1. RXD0 dive with the ETH_NRST dodge (hand-verified coordinates)
add_track(MM(128.25), MM(133.9375), MM(128.25), MM(134.6), "RMII_RXD0",
          F, 0.2)
add_track(MM(128.25), MM(134.6), MM(128.35), MM(135.9), "RMII_RXD0", F, 0.2)
add_via(MM(128.35), MM(135.9), "RMII_RXD0")
add_track(MM(128.35), MM(135.9), MM(130.9), MM(136.9), "RMII_RXD0", B, 0.2)
add_via(MM(130.9), MM(136.9), "RMII_RXD0")
add_track(MM(130.9), MM(136.9), MM(131.87), MM(138.0), "RMII_RXD0", F, 0.2)

# 2. U4.9 VDDIO fanout (hand-verified)
add_track(MM(128.75), MM(133.9375), MM(128.85), MM(134.9), "+3V3", F, 0.2)
add_via(MM(128.85), MM(134.9), "+3V3")

# 3. generic fanout for every GND/+3V3 SMD pad and tab
ic_refs = ["U3", "U4", "U5", "U1", "U2"]
targets = []
for ref in ic_refs:
    fp = board.FindFootprintByReference(ref)
    for pad in fp.Pads():
        if pad.GetNetname() in ("GND", "+3V3") and \
                pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            targets.append((ref, pad))
for fp in board.Footprints():
    ref = fp.GetReference()
    if ref in ic_refs:
        continue
    for pad in fp.Pads():
        if pad.GetNetname() in ("GND", "+3V3") and \
                pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            targets.append((ref, pad))

# skip U4.9 - already done above
fixed, failed = 0, []
for ref, pad in targets:
    if ref == "U4" and pad.GetName() == "9":
        continue
    netname = pad.GetNetname()
    netcode = pad.GetNetCode()
    ppos = pad.GetPosition()
    fp = board.FindFootprintByReference(ref)
    fpos = fp.GetPosition()
    half = max(pad.GetSize().x, pad.GetSize().y) / 2
    if pcbnew.ToMM(half) > 1.2:      # tab / EP: via straight in
        items = local_items(ppos.x, ppos.y, MM(2), netcode)
        if not collide(items, circ_sh(ppos.x, ppos.y), (F, B)):
            add_via(ppos.x, ppos.y, netname)
            fixed += 1
            continue
    dx, dy = ppos.x - fpos.x, ppos.y - fpos.y
    if abs(dx) > abs(dy):
        ux, uy = (1 if dx > 0 else -1), 0
    else:
        ux, uy = 0, (1 if dy > 0 else -1)
    items = local_items(ppos.x, ppos.y, MM(4), netcode)
    cands = []
    step = MM(0.1)
    for ix in range(-30, 31):
        for iy in range(-30, 31):
            vx, vy = ppos.x + ix * step, ppos.y + iy * step
            d = math.hypot(vx - ppos.x, vy - ppos.y)
            if d < MM(0.25):
                continue
            cands.append((d, vx, vy))
    cands.sort()
    placed = False
    for d, vx, vy in cands:
        if collide(items, circ_sh(vx, vy), (F, B)):
            continue
        path = None
        for sgn in (1, -1, 0):
            if sgn == 0:
                if not collide(items, seg_sh(ppos.x, ppos.y, vx, vy), (F,)):
                    path = [(ppos.x, ppos.y, vx, vy)]
                break
            wx = ppos.x + sgn * ux * MM(0.6)
            wy = ppos.y + sgn * uy * MM(0.6)
            if not collide(items, seg_sh(ppos.x, ppos.y, wx, wy), (F,)) \
                    and not collide(items, seg_sh(wx, wy, vx, vy), (F,)):
                path = [(ppos.x, ppos.y, wx, wy), (wx, wy, vx, vy)]
                break
        if path is None:
            continue
        for (a, b2, c2, d2) in path:
            add_track(a, b2, c2, d2, netname)
        add_via(vx, vy, netname)
        placed = True
        break
    if placed:
        fixed += 1
    else:
        failed.append((ref, pad.GetName(), netname))

print("fanout ok:", fixed)
if failed:
    print("FAILED:", failed)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved")
