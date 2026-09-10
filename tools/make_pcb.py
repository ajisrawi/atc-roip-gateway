"""Build the ATC RoIP Gateway PCB from the exported netlist.

Run with KiCad's Python:
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools/make_pcb.py

Creates hardware/atc-roip-gateway/atc-roip-gateway.kicad_pcb:
  - all footprints imported and net-assigned from netlist.net
  - 4-layer stackup (F.Cu / In1.Cu GND / In2.Cu +3V3 / B.Cu)
  - floorplan: RJ45+PHY left, MCU centre, codec + isolation + DB25 right,
    power strip along the bottom; automatic courtyard de-overlap pass
  - board outline 125 x 95 mm + 4x M3 mounting holes
  - GND / +3V3 inner plane zones, GNDA pour in the analog region
  - Specctra DSN export for autorouting
"""
import os
import re

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HW = os.path.join(ROOT, "hardware", "atc-roip-gateway")
NETLIST = os.path.join(HW, "netlist.net")
PCB = os.path.join(HW, "atc-roip-gateway.kicad_pcb")
DSN = os.path.join(HW, "atc-roip-gateway.dsn")
FPDIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"

BX0, BY0, BX1, BY1 = 100.0, 100.0, 225.0, 195.0
EDGE_MARGIN = 1.0
GAP = 0.35          # extra courtyard spacing, mm


def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def parse_netlist(path):
    text = open(path, encoding="utf-8").read()
    comps = {}
    for m in re.finditer(
            r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\)\s+'
            r'(?:\(footprint "([^"]*)"\))?', text):
        comps[m.group(1)] = (m.group(2), m.group(3) or "")
    nets = {}
    for m in re.finditer(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)', text):
        start = m.start()
        d = 0
        j = start
        while True:
            c = text[j]
            if c == '(':
                d += 1
            elif c == ')':
                d -= 1
                if d == 0:
                    break
            j += 1
        block = text[start:j + 1]
        nodes = re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', block)
        nets[m.group(1)] = [(r, p) for r, p in nodes]
    return comps, nets


# ref -> (x, y, rot).  Anchors (never moved by the de-overlap pass):
ANCHORS = {"J1", "J4", "J5", "U1", "U3", "U5", "L1",
           "T1", "T2", "T3", "T4", "U6", "U7", "U8", "U9",
           "H1", "H2", "H3", "H4", "J2", "J3"}

PLACE = {
    # network, left edge
    "J4": (113.5, 132, 0),      # RJ45, face oriented later
    "U4": (129, 132, 0),
    "Y2": (129, 144, 0), "C22": (124, 149, 0), "C23": (134, 149, 0),
    "C24": (124, 122, 90), "C40": (129, 118, 0), "C41": (135, 122, 90),
    "R10": (137, 138, 90), "R11": (124, 126, 90), "R12": (135, 126, 90),
    "R15": (124, 142, 90), "C25": (124, 145, 0),
    "R17": (123, 122, 90), "R18": (123, 127, 90),
    "R19": (123, 132, 90), "R20": (123, 137, 90),
    "FB3": (112, 116, 0), "R13": (106, 116, 0), "R14": (118, 116, 0),
    "C26": (110, 146, 0), "C27": (116, 146, 0),
    # MCU centre
    "U3": (157, 130, 0),
    "Y1": (146, 144, 0), "C10": (141, 149, 0), "C11": (151, 149, 0),
    "C12": (142, 116, 0), "R2": (147, 116, 90),
    "C13": (166, 144, 0), "C14": (171, 144, 0),
    "C15": (142, 120, 0), "C16": (147, 120, 0), "C17": (152, 120, 0),
    "C18": (162, 120, 0), "C19": (167, 120, 0), "C20": (172, 120, 0),
    "C21": (177, 120, 0),
    "R3": (152, 116, 90), "R4": (156, 116, 90),
    "R5": (160, 116, 90), "R6": (164, 116, 90),
    "J2": (140, 107, 90), "J3": (157, 107, 90),
    "R7": (170, 106, 0), "R8": (175, 106, 0), "R9": (180, 106, 0),
    "D5": (170, 110, 0), "D6": (175, 110, 0), "D7": (180, 110, 0),
    # codec
    "U5": (180, 132, 0),
    "C28": (175, 141, 0), "C29": (180, 141, 0),
    "C30": (172, 124, 90), "R21": (175, 124, 90),
    "C31": (178, 124, 90), "R22": (181, 124, 90),
    "C32": (185, 141, 0), "C33": (185, 145, 0),
    "C34": (172, 114, 0), "C35": (177, 114, 0), "C36": (182, 114, 0),
    # isolation + DB25, right edge
    "T1": (196, 112, 0), "T2": (196, 124, 0),
    "T3": (196, 136, 0), "T4": (196, 148, 0),
    "R23": (188.5, 109, 90), "R24": (188.5, 114, 90),
    "R25": (188.5, 122, 90),
    "R28": (188.5, 133, 90), "R29": (188.5, 138, 90),
    "R30": (188.5, 146, 90),
    "U6": (193, 155, 0), "U7": (193, 161.5, 0),
    "U8": (193, 168, 0), "U9": (193, 174.5, 0),
    "R26": (186, 154, 90), "R27": (186, 159, 90),
    "R31": (186, 164, 90), "R32": (186, 169, 90),
    "J5": (214, 147, 0),        # DB25, face oriented later
    # power strip along the bottom
    "J1": (110, 180, 0),
    "F1": (120, 183, 90), "D2": (126, 183, 0), "D1": (134, 183, 0),
    "C1": (142.5, 183, 0), "C2": (149, 183, 90),
    "U1": (161, 182, 0), "D3": (171, 188, 0), "L1": (179, 180, 0),
    "C3": (192, 183, 0), "C4": (200, 183, 90),
    "U2": (207, 181, 0), "C5": (202, 176, 90), "C6": (213, 176, 90),
    "FB1": (216, 183, 0), "C7": (220, 183, 90), "C8": (223, 183, 90),
    "FB2": (216, 187, 0),
    "R1": (106, 173, 90), "D4": (111, 173, 0),
}

# connector face directions (unit vector the mating face must point at)
FACE = {"J4": (-1, 0), "J5": (1, 0), "J1": (0, 1)}


def orient_connector(fp, face):
    """Rotate fp so its pads sit opposite the requested face direction."""
    best, best_dot = 0, 1e9
    for rot in (0, 90, 180, 270):
        fp.SetOrientationDegrees(rot)
        body = fp.GetBoundingBox(False)
        pads_x = pads_y = n = 0
        for pad in fp.Pads():
            p = pad.GetPosition()
            pads_x += p.x
            pads_y += p.y
            n += 1
        cx, cy = body.GetCenter().x, body.GetCenter().y
        vx, vy = pads_x / n - cx, pads_y / n - cy
        dot = vx * face[0] + vy * face[1]     # want pads AWAY from face
        if dot < best_dot:
            best_dot, best = dot, rot
    fp.SetOrientationDegrees(best)


def boxes_overlap(a, b, margin_iu):
    return (a.GetLeft() - margin_iu < b.GetRight() and
            b.GetLeft() - margin_iu < a.GetRight() and
            a.GetTop() - margin_iu < b.GetBottom() and
            b.GetTop() - margin_iu < a.GetBottom())


def deoverlap(board, movable):
    fps = {fp.GetReference(): fp for fp in board.Footprints()}
    margin = pcbnew.FromMM(GAP)
    for _ in range(400):
        moved = False
        items = list(fps.values())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                ra, rb = a.GetReference(), b.GetReference()
                ba = a.GetBoundingBox(False)
                bb = b.GetBoundingBox(False)
                if not boxes_overlap(ba, bb, margin):
                    continue
                # penetration on each axis
                px = min(ba.GetRight(), bb.GetRight()) - \
                    max(ba.GetLeft(), bb.GetLeft()) + margin
                py = min(ba.GetBottom(), bb.GetBottom()) - \
                    max(ba.GetTop(), bb.GetTop()) + margin
                move_a = ra in movable
                move_b = rb in movable
                if not (move_a or move_b):
                    continue
                if px < py:
                    d = px
                    sign = 1 if ba.GetCenter().x < bb.GetCenter().x else -1
                    da, db = (-sign * d, 0), (sign * d, 0)
                else:
                    d = py
                    sign = 1 if ba.GetCenter().y < bb.GetCenter().y else -1
                    da, db = (0, -sign * d), (0, sign * d)
                if move_a and move_b:
                    da = (da[0] // 2, da[1] // 2)
                    db = (db[0] // 2, db[1] // 2)
                for fp2, dd, can in ((a, da, move_a), (b, db, move_b)):
                    if not can:
                        continue
                    p = fp2.GetPosition()
                    nx = p.x + int(dd[0])
                    ny = p.y + int(dd[1])
                    half_w = fp2.GetBoundingBox(False).GetWidth() // 2
                    half_h = fp2.GetBoundingBox(False).GetHeight() // 2
                    nx = max(pcbnew.FromMM(BX0 + EDGE_MARGIN) + half_w,
                             min(pcbnew.FromMM(BX1 - EDGE_MARGIN) - half_w, nx))
                    ny = max(pcbnew.FromMM(BY0 + EDGE_MARGIN) + half_h,
                             min(pcbnew.FromMM(BY1 - EDGE_MARGIN) - half_h, ny))
                    if (nx, ny) != (p.x, p.y):
                        fp2.SetPosition(pcbnew.VECTOR2I(nx, ny))
                        moved = True
        if not moved:
            return True
    return False


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    return pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)


def main():
    comps, nets = parse_netlist(NETLIST)
    if os.path.exists(PCB):
        os.remove(PCB)
    board = pcbnew.NewBoard(PCB)
    board.GetDesignSettings().SetCopperLayerCount(4)

    netmap = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni
    padnet = {}
    for name, nodes in nets.items():
        for ref, pad in nodes:
            padnet[(ref, pad)] = name

    issues = []
    movable = set()
    for ref, (value, fpid) in sorted(comps.items()):
        if ref.startswith("#"):
            continue
        fp = load_fp(fpid) if fpid else None
        if fp is None:
            issues.append((ref, fpid or "no footprint"))
            continue
        fp.SetReference(ref)
        fp.SetValue(value)
        board.Add(fp)
        x, y, rot = PLACE.get(ref, (150, 165, 0))
        if ref not in PLACE:
            issues.append((ref, "no placement -> parked"))
        fp.SetPosition(mm(x, y))
        if ref in FACE:
            orient_connector(fp, FACE[ref])
        else:
            fp.SetOrientationDegrees(rot)
        if ref not in ANCHORS:
            movable.add(ref)
        for pad in fp.Pads():
            key = (ref, pad.GetName())
            if key in padnet:
                pad.SetNet(netmap[padnet[key]])

    for i, (hx, hy) in enumerate(
            [(105, 105), (196, 103.6), (105, 190), (196, 191.4)], 1):
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, "MountingHole.pretty"),
                                  "MountingHole_3.2mm_M3")
        fp.SetReference(f"H{i}")
        fp.SetValue("M3")
        board.Add(fp)
        fp.SetPosition(mm(hx, hy))

    converged = deoverlap(board, movable)

    # park reference silkscreen just above each footprint so refs never sit
    # on pads or other silk (assembly still readable, fab won't clip them)
    for fp in board.Footprints():
        bb = fp.GetBoundingBox(False)
        ref = fp.Reference()
        ref.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
        ref.SetTextThickness(pcbnew.FromMM(0.13))
        ref.SetTextAngleDegrees(0)
        ref.SetPosition(pcbnew.VECTOR2I(bb.GetCenter().x,
                                        bb.GetTop() - pcbnew.FromMM(0.8)))

    pts = [(BX0, BY0), (BX1, BY0), (BX1, BY1), (BX0, BY1)]
    for i in range(4):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(mm(*pts[i]))
        seg.SetEnd(mm(*pts[(i + 1) % 4]))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)

    # collect NPTH holes so plane zones keep clear of them
    npth = []
    for fp in board.Footprints():
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                p = pad.GetPosition()
                r = max(pad.GetDrillSize().x, pad.GetDrillSize().y) / 2
                npth.append((p.x, p.y, r + pcbnew.FromMM(0.6)))

    def add_zone(layer, netname, rect, priority=0):
        import math
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNetCode(netmap[netname].GetNetCode())
        z.SetAssignedPriority(priority)
        ol = z.Outline()
        ol.NewOutline()
        x0, y0, x1, y1 = rect
        for px, py in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            ol.Append(pcbnew.FromMM(px), pcbnew.FromMM(py))
        for hx, hy, hr in npth:
            if not (pcbnew.FromMM(x0) < hx < pcbnew.FromMM(x1) and
                    pcbnew.FromMM(y0) < hy < pcbnew.FromMM(y1)):
                continue
            hole = ol.NewHole()
            for k in range(12):
                a = 2 * math.pi * k / 12
                ol.Append(int(hx + hr * math.cos(a)),
                          int(hy + hr * math.sin(a)), 0, hole)
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        board.Add(z)

    E = 0.65    # plane inset from board edge
    add_zone(pcbnew.In1_Cu, "GND", (BX0 + E, BY0 + E, BX1 - E, BY1 - E))
    add_zone(pcbnew.In2_Cu, "+3V3", (BX0 + E, BY0 + E, BX1 - E, BY1 - E))
    # NOTE: a B.Cu GNDA pour over the analog region is added during routing
    # polish; pre-route it only creates isolated islands.

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print("wrote", PCB)
    print("de-overlap converged:", converged)
    if issues:
        print("ISSUES:")
        for m in issues:
            print("  ", m)
    ok = pcbnew.ExportSpecctraDSN(board, DSN)
    print("DSN export:", ok)


if __name__ == "__main__":
    main()

