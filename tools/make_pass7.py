import io

src = r"C:\Users\ahmad\Documents\ATC ROIP\tools\fanout_pass6.py"
dst = r"C:\Users\ahmad\Documents\ATC ROIP\tools\fanout_pass7.py"
s = io.open(src, encoding='utf-8').read()

s = s.replace('''    ('U3', '11', '+3V3'), ('U3', '27', '+3V3'), ('U3', '49', 'GND'),
    ('U3', '74', 'GND'), ('U3', '75', '+3V3'),
    ('U4', '1', '+3V3'), ('U4', '9', '+3V3'),
    ('U5', '1', '+3V3'),
    ('U1', '3', 'GND'), ('U2', '2', '+3V3'),''',
              '''    ('U3', '11', '+3V3'), ('U3', '27', '+3V3'), ('U3', '49', 'GND'),
    ('U3', '74', 'GND'),
    ('U4', '1', '+3V3'), ('U4', '9', '+3V3'),
    ('U5', '1', '+3V3'),''')

s = s.replace('''    gx0 = ppos.x + ux * pcbnew.FromMM(0.9)
    gy0 = ppos.y + uy * pcbnew.FromMM(0.9)''',
              '''    gx0, gy0 = ppos.x, ppos.y''')

s = s.replace('''            if ux and (vx - ppos.x) * ux < pcbnew.FromMM(0.3):
                continue
            if uy and (vy - ppos.y) * uy < pcbnew.FromMM(0.3):
                continue''',
              '''            if math.hypot(vx - ppos.x, vy - ppos.y) < pcbnew.FromMM(0.7):
                continue''')

s = s.replace('''        wx = ppos.x + ux * pcbnew.FromMM(0.6)
        wy = ppos.y + uy * pcbnew.FromMM(0.6)
        path = None
        if not collide(items, seg(ppos.x, ppos.y, wx, wy), (pcbnew.F_Cu,)) \\
                and not collide(items, seg(wx, wy, vx, vy), (pcbnew.F_Cu,)):
            path = [(ppos.x, ppos.y, wx, wy), (wx, wy, vx, vy)]
        elif not collide(items, seg(ppos.x, ppos.y, vx, vy),
                         (pcbnew.F_Cu,)):
            path = [(ppos.x, ppos.y, vx, vy)]
        if path is None:
            continue''',
              '''        path = None
        for sgn in (1, -1, 0):
            if sgn == 0:
                if not collide(items, seg(ppos.x, ppos.y, vx, vy),
                               (pcbnew.F_Cu,)):
                    path = [(ppos.x, ppos.y, vx, vy)]
                break
            wx = ppos.x + sgn * ux * pcbnew.FromMM(0.6)
            wy = ppos.y + sgn * uy * pcbnew.FromMM(0.6)
            if not collide(items, seg(ppos.x, ppos.y, wx, wy),
                           (pcbnew.F_Cu,)) \\
                    and not collide(items, seg(wx, wy, vx, vy),
                                    (pcbnew.F_Cu,)):
                path = [(ppos.x, ppos.y, wx, wy), (wx, wy, vx, vy)]
                break
        if path is None:
            continue''')

io.open(dst, 'w', encoding='utf-8').write(s)
print('written pass7')
