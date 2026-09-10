"""Pass 6: fab-standard min-via rules, tighter zone fill, finish orphans."""
import math
import functools
import builtins

print = functools.partial(builtins.print, flush=True)
import pcbnew

HW = r"C:\Users\ahmad\Documents\ATC ROIP\hardware\atc-roip-gateway"
PCB = HW + r"\atc-roip-gateway.kicad_pcb"

TARGETS = [
    ('U3', '27', '+3V3'), ('U3', '74', 'GND'),
    ('U4', '1', '+3V3'), ('U4', '9', '+3V3'),
]

VIA_DIA, VIA_DRILL, TRACK_W, CLR = 0.45, 0.2, 0.2, 0.155

board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()

# fab-standard (JLC 4-layer) minimums so small vias are legal
ds = board.GetDesignSettings()
ds.m_ViasMinSize = pcbnew.FromMM(0.45)
ds.m_MinThroughDrill = pcbnew.FromMM(0.2)
ds.m_HoleToHoleMin = pcbnew.FromMM(0.2)

# tighter zone fill so plane copper reaches vias in congested areas
for z in board.Zones():
    z.SetMinThickness(pcbnew.FromMM(0.15))
    z.SetLocalClearance(pcbnew.FromMM(0.22))

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


def local_items(cx, cy, r_iu, netcode):
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


def add_track(x1, y1, x2, y2, netname):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetLayer(pcbnew.F_Cu)
    t.SetWidth(pcbnew.FromMM(TRACK_W))
    t.SetNet(nets[netname])
    board.Add(t)
    all_items.append(t)


def add_via(x, y, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetWidth(pcbnew.FromMM(VIA_DIA))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(nets[netname])
    board.Add(v)
    all_items.append(v)


fixed, failed = 0, []
for ref, pad_no, netname in TARGETS:
    fp = board.FindFootprintByReference(ref)
    pad = next(p for p in fp.Pads() if p.GetName() == pad_no)
    ppos = pad.GetPosition()
    fpos = fp.GetPosition()
    netcode = pad.GetNetCode()
    half = max(pad.GetSize().x, pad.GetSize().y) / 2
    # big tab pads (regulators): via straight into the pad
    if pcbnew.ToMM(half) > 1.4:
        items = local_items(ppos.x, ppos.y, pcbnew.FromMM(2), netcode)
        if not collide(items, circ(ppos.x, ppos.y),
                       (pcbnew.F_Cu, pcbnew.B_Cu)):
            add_via(ppos.x, ppos.y, netname)
            print(f"{ref}.{pad_no} via-in-tab")
            fixed += 1
            continue
    dx, dy = ppos.x - fpos.x, ppos.y - fpos.y
    if abs(dx) > abs(dy):
        ux, uy = (1 if dx > 0 else -1), 0
    else:
        ux, uy = 0, (1 if dy > 0 else -1)
    items = local_items(ppos.x, ppos.y, pcbnew.FromMM(4), netcode)
    gx0, gy0 = ppos.x, ppos.y
    cands = []
    step = pcbnew.FromMM(0.05)
    for ix in range(-40, 41):
        for iy in range(-40, 41):
            vx, vy = gx0 + ix * step, gy0 + iy * step
            if math.hypot(vx - ppos.x, vy - ppos.y) < pcbnew.FromMM(0.25):
                continue
            cands.append((math.hypot(vx - gx0, vy - gy0), vx, vy))
    cands.sort()
    placed = False
    for d, vx, vy in cands:
        if collide(items, circ(vx, vy), (pcbnew.F_Cu, pcbnew.B_Cu)):
            continue
        path = None
        for sgn in (1, -1, 0):
            if sgn == 0:
                if not collide(items, seg(ppos.x, ppos.y, vx, vy),
                               (pcbnew.F_Cu,)):
                    path = [(ppos.x, ppos.y, vx, vy)]
                break
            wx = ppos.x + sgn * ux * pcbnew.FromMM(0.6)
            wy = ppos.y + sgn * uy * pcbnew.FromMM(0.6)
            if not collide(items, seg(ppos.x, ppos.y, wx, wy),
                           (pcbnew.F_Cu,)) \
                    and not collide(items, seg(wx, wy, vx, vy),
                                    (pcbnew.F_Cu,)):
                path = [(ppos.x, ppos.y, wx, wy), (wx, wy, vx, vy)]
                break
        if path is None:
            continue
        for (a, b, c2, d2) in path:
            add_track(a, b, c2, d2, netname)
        add_via(vx, vy, netname)
        print(f"{ref}.{pad_no} via at ({pcbnew.ToMM(vx):.2f},"
              f"{pcbnew.ToMM(vy):.2f})")
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
