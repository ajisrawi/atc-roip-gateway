"""Pass 5: dense grid search with small vias for the last orphan pads."""
import math
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

VIA_DIA, VIA_DRILL, TRACK_W, CLR = 0.45, 0.25, 0.2, 0.2

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()

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
    return (p.x, p.y, pcbnew.FromMM(2))


def local_items(cx, cy, r_iu, netcode, same_ptr):
    out = []
    for it in all_items:
        if it.GetNetCode() == netcode:
            continue
        ax, ay, extra = item_anchor(it)
        if math.hypot(ax - cx, ay - cy) < r_iu + extra + pcbnew.FromMM(1.5):
            out.append(it)
    return out


def collide(items, shape, layers):
    for it in items:
        for layer in layers:
            if hasattr(it, "IsOnLayer") and not it.IsOnLayer(layer):
                continue
            if it.GetEffectiveShape(layer).Collide(shape,
                                                   pcbnew.FromMM(CLR)):
                return True
            break
    return False


def seg(x1, y1, x2, y2):
    return pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(int(x1), int(y1)),
                                pcbnew.VECTOR2I(int(x2), int(y2)),
                                pcbnew.FromMM(TRACK_W))


def circ(x, y):
    return pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(int(x), int(y)),
                               pcbnew.FromMM(VIA_DIA / 2))


fixed, failed = 0, []
for ref, pad_no, netname in TARGETS:
    fp = board.FindFootprintByReference(ref)
    pad = next(p for p in fp.Pads() if p.GetName() == pad_no)
    ppos = pad.GetPosition()
    fpos = fp.GetPosition()
    netcode = pad.GetNetCode()
    dx, dy = ppos.x - fpos.x, ppos.y - fpos.y
    if abs(dx) > abs(dy):
        ux, uy = (1 if dx > 0 else -1), 0
    else:
        ux, uy = 0, (1 if dy > 0 else -1)
    items = local_items(ppos.x, ppos.y, pcbnew.FromMM(3.5), netcode, pad)

    # candidate via spots: grid, sorted by distance from a point slightly
    # outward of the pad
    gx0 = ppos.x + ux * pcbnew.FromMM(0.9)
    gy0 = ppos.y + uy * pcbnew.FromMM(0.9)
    cands = []
    step = pcbnew.FromMM(0.2)
    for ix in range(-14, 15):
        for iy in range(-14, 15):
            vx, vy = gx0 + ix * step, gy0 + iy * step
            # stay outward of the pad row
            if ux and (vx - ppos.x) * ux < pcbnew.FromMM(0.35):
                continue
            if uy and (vy - ppos.y) * uy < pcbnew.FromMM(0.35):
                continue
            d = math.hypot(vx - gx0, vy - gy0)
            cands.append((d, vx, vy))
    cands.sort()

    placed = False
    for d, vx, vy in cands:
        if collide(items, circ(vx, vy), (pcbnew.F_Cu, pcbnew.B_Cu)):
            continue
        # 2-segment path: out 0.6 mm then direct to via
        wx = ppos.x + ux * pcbnew.FromMM(0.6)
        wy = ppos.y + uy * pcbnew.FromMM(0.6)
        if collide(items, seg(ppos.x, ppos.y, wx, wy), (pcbnew.F_Cu,)):
            continue
        if collide(items, seg(wx, wy, vx, vy), (pcbnew.F_Cu,)):
            # try direct from pad instead
            if collide(items, seg(ppos.x, ppos.y, vx, vy), (pcbnew.F_Cu,)):
                continue
            wx, wy = None, None
        t1 = pcbnew.PCB_TRACK(board)
        if wx is not None:
            t1.SetStart(pcbnew.VECTOR2I(ppos.x, ppos.y))
            t1.SetEnd(pcbnew.VECTOR2I(int(wx), int(wy)))
        else:
            t1.SetStart(pcbnew.VECTOR2I(ppos.x, ppos.y))
            t1.SetEnd(pcbnew.VECTOR2I(int(vx), int(vy)))
        t1.SetLayer(pcbnew.F_Cu)
        t1.SetWidth(pcbnew.FromMM(TRACK_W))
        t1.SetNet(nets[netname])
        board.Add(t1)
        all_items.append(t1)
        if wx is not None:
            t2 = pcbnew.PCB_TRACK(board)
            t2.SetStart(pcbnew.VECTOR2I(int(wx), int(wy)))
            t2.SetEnd(pcbnew.VECTOR2I(int(vx), int(vy)))
            t2.SetLayer(pcbnew.F_Cu)
            t2.SetWidth(pcbnew.FromMM(TRACK_W))
            t2.SetNet(nets[netname])
            board.Add(t2)
            all_items.append(t2)
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(vx), int(vy)))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetDrill(pcbnew.FromMM(VIA_DRILL))
        v.SetWidth(pcbnew.FromMM(VIA_DIA))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(nets[netname])
        board.Add(v)
        all_items.append(v)
        placed = True
        print(f"{ref}.{pad_no} via at ({pcbnew.ToMM(vx):.2f},"
              f"{pcbnew.ToMM(vy):.2f})")
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
