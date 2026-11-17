import cairo, math, json, random, subprocess, sys, os
W, H, FPS = 1080, 1920, 30
EP = os.environ['EP']
TIM = json.load(open(EP + '/timing.json'))
RED = (0.80, 0.07, 0.12)
SIL = (0.02, 0.02, 0.03)

def ps(i): return TIM[i]['start']

# ---------------- scenes (phrase index ranges) ----------------
SCENES = [('A', 0), ('B', 2), ('C', 5), ('D', 7), ('E', 11), ('F', 13), ('S', 15), ('G', 16)]
TOTAL = TIM[-1]['end'] + 1.0
def scene_bounds():
    out = []
    for k, (name, pi) in enumerate(SCENES):
        s = 0.0 if k == 0 else ps(pi) - 0.12
        e = TOTAL if k == len(SCENES) - 1 else ps(SCENES[k + 1][1]) - 0.12
        out.append((name, s, e))
    return out

# ---------------- captions ----------------
def build_words():
    words = []
    for p in TIM:
        toks = p['text'].replace('...', ' ').split()
        wts = [len(w) + 2 for w in toks]
        tot = sum(wts); t = p['start']; dur = p['end'] - p['start']
        for w, wt in zip(toks, wts):
            d = dur * wt / tot
            words.append({'w': w.strip(',').upper(), 't0': t, 't1': t + d, 'end_phrase': False})
            t += d
        words[-1]['end_phrase'] = True
    # groups of <=3 words, break at phrase end
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w['end_phrase'] or w['w'].endswith('.'):
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    for i, g in enumerate(groups):
        g0 = g[0]['t0']; g1 = groups[i + 1][0]['t0'] if i + 1 < len(groups) else g[-1]['t1'] + 0.6
        if g1 - g[-1]['t1'] > 0.5: g1 = g[-1]['t1'] + 0.35
        for w in g: w['g0'], w['g1'] = g0, g1
    return groups
GROUPS = build_words()

def draw_captions(ctx, t):
    for g in GROUPS:
        if g[0]['g0'] <= t < g[0]['g1']:
            break
    else:
        return
    ctx.new_path()
    age = t - g[0]['g0']
    pop = 1.0 + 0.12 * max(0, 1 - age / 0.12)
    ctx.select_font_face('Anton', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    size = 104
    ctx.set_font_size(size)
    txt = [w['w'] for w in g]
    space = ctx.text_extents(' ').x_advance
    widths = [ctx.text_extents(s).x_advance for s in txt]
    total = sum(widths) + space * (len(txt) - 1)
    scale = min(1.0, 940 / total) * pop
    cy = 1060
    ctx.save(); ctx.translate(W / 2, cy); ctx.scale(scale, scale)
    x = -total / 2
    for s, wdt, w in zip(txt, widths, g):
        active = w['t0'] <= t < w['t1']
        ctx.move_to(x, size * 0.36); ctx.text_path(s)
        ctx.set_source_rgb(0, 0, 0); ctx.set_line_width(14); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
        if active: ctx.set_source_rgb(1.0, 0.23, 0.25)
        else: ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        x += wdt + space
    ctx.restore()

# ---------------- drawing helpers ----------------
def sky(ctx, top=(0.04, 0.05, 0.08), bot=(0.26, 0.20, 0.17), horizon=1350):
    g = cairo.LinearGradient(0, 0, 0, horizon)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bot)
    ctx.set_source(g); ctx.rectangle(0, 0, W, H); ctx.fill()

def moon(ctx, x, y, r):
    g = cairo.RadialGradient(x, y, r * 0.8, x, y, r * 4)
    g.add_color_stop_rgba(0, 0.95, 0.88, 0.72, 0.35); g.add_color_stop_rgba(1, 0.95, 0.88, 0.72, 0)
    ctx.set_source(g); ctx.arc(x, y, r * 4, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(0.93, 0.87, 0.74); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(0.75, 0.68, 0.55, 0.5)
    for dx, dy, rr in [(-0.3, -0.2, 0.2), (0.25, 0.3, 0.14), (0.1, -0.35, 0.09)]:
        ctx.arc(x + dx * r, y + dy * r, rr * r, 0, 2 * math.pi); ctx.fill()

def cathedral(ctx, x, base, s, col):
    ctx.set_source_rgb(*col)
    ctx.rectangle(x - 160 * s, base - 300 * s, 320 * s, 300 * s); ctx.fill()  # nave block
    ctx.rectangle(x + 40 * s, base - 520 * s, 110 * s, 520 * s); ctx.fill()   # tower
    ctx.move_to(x + 30 * s, base - 520 * s); ctx.line_to(x + 95 * s, base - 900 * s); ctx.line_to(x + 160 * s, base - 520 * s); ctx.fill()  # spire
    ctx.rectangle(x + 92 * s, base - 960 * s, 6 * s, 70 * s); ctx.fill()
    ctx.move_to(x - 160 * s, base - 300 * s); ctx.line_to(x - 60 * s, base - 380 * s); ctx.line_to(x + 40 * s, base - 300 * s); ctx.fill()

def houses(ctx, base, rng, col, h0, h1, lit=0.25, seed_w=(110, 190), windows=True):
    x = -40
    while x < W + 40:
        w = rng.uniform(*seed_w); h = rng.uniform(h0, h1)
        ctx.set_source_rgb(*col)
        ctx.rectangle(x, base - h, w, h + 2); ctx.fill()
        ctx.move_to(x - 8, base - h); ctx.line_to(x + w / 2, base - h - w * 0.75); ctx.line_to(x + w + 8, base - h); ctx.fill()
        if rng.random() < 0.4:
            ctx.rectangle(x + w * 0.7, base - h - w * 0.7, 14, 60); ctx.fill()  # chimney
        if windows:
            rows = int(h // 70)
            for r in range(rows):
                for c in range(2):
                    if rng.random() < lit:
                        wx = x + w * (0.22 + 0.4 * c); wy = base - h + 25 + r * 70
                        g = cairo.RadialGradient(wx + 9, wy + 13, 2, wx + 9, wy + 13, 40)
                        g.add_color_stop_rgba(0, 0.95, 0.65, 0.25, 0.35); g.add_color_stop_rgba(1, 0.95, 0.65, 0.25, 0)
                        ctx.set_source(g); ctx.arc(wx + 9, wy + 13, 40, 0, 2 * math.pi); ctx.fill()
                        ctx.set_source_rgb(0.92, 0.62, 0.25); ctx.rectangle(wx, wy, 18, 26); ctx.fill()
                        ctx.set_source_rgb(*col); ctx.rectangle(wx + 8, wy, 2, 26); ctx.fill(); ctx.rectangle(wx, wy + 12, 18, 2); ctx.fill()
        x += w + rng.uniform(-6, 4)

def ground(ctx, top, col=(0.07, 0.06, 0.06)):
    g = cairo.LinearGradient(0, top, 0, H)
    g.add_color_stop_rgb(0, 0.13, 0.11, 0.10); g.add_color_stop_rgb(1, *col)
    ctx.set_source(g); ctx.rectangle(0, top, W, H - top); ctx.fill()
    rng = random.Random(5)
    for row in range(40):
        y = top + (row ** 1.6) * 3.2
        if y > H: break
        sz = 10 + row * 2.2
        x = rng.uniform(-sz, 0)
        while x < W:
            ctx.set_source_rgba(0.35, 0.30, 0.26, 0.08 + 0.05 * rng.random())
            ctx.save(); ctx.translate(x + sz / 2, y); ctx.scale(sz / 2, sz / 5); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
            x += sz * rng.uniform(1.05, 1.3)

def fog(ctx, y, h, a=0.25):
    g = cairo.LinearGradient(0, y - h, 0, y + h)
    g.add_color_stop_rgba(0, 0.6, 0.55, 0.5, 0); g.add_color_stop_rgba(0.5, 0.6, 0.55, 0.5, a); g.add_color_stop_rgba(1, 0.6, 0.55, 0.5, 0)
    ctx.set_source(g); ctx.rectangle(0, y - h, W, 2 * h); ctx.fill()

def limb(ctx, pts, w):
    ctx.set_line_width(w); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    ctx.stroke()

def dancer(ctx, x, y, s, t, ph, dress=True, speed=1.0, collapse=0.0, col=SIL, frenzy=1.0):
    """Feet at (x,y). Height ~ 190*s."""
    w = 2 * math.pi * 0.9 * speed
    a = t * w + ph
    ctx.save(); ctx.translate(x, y)
    if collapse > 0:
        c = min(1, collapse); c = c * c * (3 - 2 * c)
        ctx.rotate((1 if math.sin(ph * 7) > 0 else -1) * c * 1.45)
    ctx.scale(s, s)
    ctx.set_source_rgb(*col)
    bob = abs(math.sin(a)) * 8 * frenzy
    sway = math.sin(a) * 0.28 * frenzy
    hip = (math.sin(a) * 10 * frenzy, -95 - bob)
    neck = (hip[0] + math.sin(sway) * 62, hip[1] - math.cos(sway) * 62)
    head = (neck[0] + math.sin(sway * 1.6 + 0.2 * math.sin(a * 2)) * 18, neck[1] - 20)
    # legs
    for side in (-1, 1):
        lift = max(0, math.sin(a + (0 if side > 0 else math.pi))) * frenzy
        knee = (hip[0] + side * 14 + lift * 18 * side, hip[1] + 48 - lift * 22)
        foot = (hip[0] + side * 18 + lift * 6 * side, -lift * 26)
        limb(ctx, [hip, knee, foot], 13)
    # torso
    limb(ctx, [hip, neck], 30)
    if dress:
        ctx.move_to(hip[0] - 16, hip[1] - 12); ctx.line_to(hip[0] + 16, hip[1] - 12)
        flare = 40 + 10 * math.sin(a * 2)
        ctx.line_to(hip[0] + flare + sway * 30, hip[1] + 62); ctx.line_to(hip[0] - flare + sway * 30, hip[1] + 62); ctx.close_path(); ctx.fill()
    # arms
    for side in (-1, 1):
        up = 0.5 + 0.5 * math.sin(a * 1.0 + side * 1.3 + ph)
        sh = (neck[0] + side * 12, neck[1] + 8)
        ang = side * (0.4 + up * 2.2 * frenzy)
        elbow = (sh[0] + math.sin(ang) * 34, sh[1] + math.cos(ang) * 34)
        ang2 = ang + side * (0.6 + 0.6 * math.sin(a * 2 + side))
        hand = (elbow[0] + math.sin(ang2) * 32, elbow[1] + math.cos(ang2) * 32)
        limb(ctx, [sh, elbow, hand], 10)
    ctx.arc(head[0], head[1], 17, 0, 2 * math.pi); ctx.fill()
    if dress:
        ctx.arc(head[0] - 6, head[1] - 14, 9, 0, 2 * math.pi); ctx.fill()  # coif
    ctx.restore()

def vignette(ctx, strength=0.85, col=(0, 0, 0)):
    g = cairo.RadialGradient(W / 2, H * 0.48, W * 0.35, W / 2, H * 0.48, H * 0.75)
    g.add_color_stop_rgba(0, *col, 0); g.add_color_stop_rgba(1, *col, strength)
    ctx.set_source(g); ctx.paint()

def title(ctx, text, y, size, alpha, font='Cinzel', col=(0.93, 0.87, 0.74), spacing=0):
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ex = ctx.text_extents(text)
    ctx.move_to(W / 2 - ex.x_advance / 2, y); ctx.text_path(text)
    ctx.set_source_rgba(0, 0, 0, 0.8 * alpha); ctx.set_line_width(8); ctx.stroke_preserve()
    ctx.set_source_rgba(*col, alpha); ctx.fill()

def ease(x): x = max(0, min(1, x)); return x * x * (3 - 2 * x)

# ---------------- cached backgrounds ----------------
def street_bg():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(100, 100)
    sky(ctx); moon(ctx, 760, 330, 70)
    cathedral(ctx, 520, 1150, 1.0, (0.10, 0.09, 0.11))
    houses(ctx, 1220, random.Random(3), (0.07, 0.06, 0.08), 260, 420, lit=0.12)
    houses(ctx, 1330, random.Random(9), (0.03, 0.03, 0.04), 380, 600, lit=0.22)
    ground(ctx, 1320); fog(ctx, 1300, 140, 0.18)
    return surf

def landscape_bg():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(100, 100)
    sky(ctx, top=(0.05, 0.05, 0.08), bot=(0.35, 0.22, 0.16), horizon=1250); moon(ctx, 260, 420, 55)
    # far hills
    ctx.set_source_rgb(0.10, 0.08, 0.09)
    ctx.move_to(-100, 1250)
    for i in range(0, W + 200, 40): ctx.line_to(i, 1150 - 60 * math.sin(i / 170) - 30 * math.sin(i / 61))
    ctx.line_to(W + 100, H); ctx.line_to(-100, H); ctx.fill()
    # shrine hill
    ctx.set_source_rgb(0.12, 0.095, 0.09)
    ctx.move_to(-100, 1400); ctx.curve_to(400, 1380, 650, 1000, 900, 1020); ctx.curve_to(1050, 1030, 1150, 1200, 1200, 1250); ctx.line_to(1200, H); ctx.line_to(-100, H); ctx.fill()
    # chapel on hill
    cx, cy = 880, 1022
    ctx.rectangle(cx - 60, cy - 110, 120, 110); ctx.fill()
    ctx.move_to(cx - 72, cy - 110); ctx.line_to(cx, cy - 175); ctx.line_to(cx + 72, cy - 110); ctx.fill()
    ctx.rectangle(cx - 4, cy - 240, 8, 70); ctx.fill(); ctx.rectangle(cx - 22, cy - 222, 44, 8); ctx.fill()
    g = cairo.RadialGradient(cx, cy - 60, 4, cx, cy - 60, 120)
    g.add_color_stop_rgba(0, 0.95, 0.6, 0.25, 0.55); g.add_color_stop_rgba(1, 0.95, 0.6, 0.25, 0)
    ctx.set_source(g); ctx.arc(cx, cy - 60, 120, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(0.95, 0.62, 0.25); ctx.move_to(cx - 12, cy - 30); ctx.line_to(cx - 12, cy - 70); ctx.arc(cx, cy - 70, 12, math.pi, 0); ctx.line_to(cx + 12, cy - 30); ctx.fill()
    # road
    ctx.set_source_rgba(0.42, 0.33, 0.26, 0.45)
    ctx.move_to(-100, 1600); ctx.curve_to(300, 1560, 600, 1300, 840, 1050); ctx.line_to(860, 1052); ctx.curve_to(650, 1330, 380, 1640, -100, 1720); ctx.fill()
    fog(ctx, 1230, 120, 0.22)
    return surf

def bg_paint(ctx, surf, t, z0, z1, dur, dx=0, dy=0):
    z = z0 + (z1 - z0) * ease(t / dur) if dur > 0 else z0
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2 + dx, -H / 2 + dy)
    ctx.set_source_surface(surf, -100, -100); ctx.paint(); ctx.restore()
    return z

# ---------------- props ----------------
def wagon(ctx, x, y, s, t):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.set_source_rgb(*SIL)
    # horse
    step = math.sin(t * 6)
    ctx.save(); ctx.translate(210, -70)
    ctx.save(); ctx.scale(70, 32); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    limb(ctx, [(45, -10), (75, -60), (100, -55)], 22)
    ctx.save(); ctx.translate(100, -55); ctx.rotate(0.5); ctx.scale(26, 12); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    for lx, ph in [(-50, 0), (-35, math.pi), (40, math.pi), (55, 0)]:
        sw = math.sin(t * 6 + ph) * 14
        limb(ctx, [(lx, 10), (lx + sw * 0.5, 45), (lx + sw, 72)], 9)
    limb(ctx, [(-68, -10), (-88, 20), (-92, 40)], 7)
    ctx.restore()
    # cart
    ctx.rectangle(-140, -120, 260, 70); ctx.fill()
    limb(ctx, [(120, -70), (170, -60)], 6)
    # people slumped in cart
    for i, px in enumerate([-110, -60, -10, 40]):
        ctx.arc(px, -132 - 4 * math.sin(t * 6 + i), 15, 0, 2 * math.pi); ctx.fill()
        ctx.rectangle(px - 14, -128, 28, 20); ctx.fill()
    for wx in (-90, 70):
        ctx.set_line_width(7); ctx.arc(wx, -40, 38, 0, 2 * math.pi); ctx.stroke()
        for k in range(6):
            an = k * math.pi / 3 + t * 3
            ctx.move_to(wx, -40); ctx.line_to(wx + math.cos(an) * 38, -40 + math.sin(an) * 38); ctx.set_line_width(4); ctx.stroke()
    ctx.restore()

def shoe(ctx, x, y, s, flip=1, col=RED):
    ctx.save(); ctx.translate(x, y); ctx.scale(s * flip, s)
    dark = (col[0] * 0.35, col[1] * 0.25, col[2] * 0.25)
    # heel block
    ctx.set_source_rgb(*dark)
    ctx.move_to(-122, -4); ctx.line_to(-80, -4); ctx.line_to(-86, 26); ctx.line_to(-116, 26); ctx.close_path(); ctx.fill()
    # body
    g = cairo.LinearGradient(0, -80, 0, 10)
    g.add_color_stop_rgb(0, min(1, col[0] * 1.3), col[1] * 1.4, col[2] * 1.4); g.add_color_stop_rgb(1, col[0] * 0.5, col[1] * 0.35, col[2] * 0.35)
    ctx.move_to(-126, 0)
    ctx.curve_to(-136, -30, -130, -66, -116, -76)
    ctx.curve_to(-90, -84, -60, -78, -40, -66)
    ctx.curve_to(-20, -54, -2, -50, 12, -52)
    ctx.curve_to(60, -58, 120, -38, 158, -18)
    ctx.curve_to(178, -8, 176, 4, 156, 6)
    ctx.curve_to(60, 12, -40, 8, -126, 0); ctx.close_path()
    ctx.set_source(g); ctx.fill_preserve(); ctx.set_source_rgba(0, 0, 0, 0.7); ctx.set_line_width(3); ctx.stroke()
    # opening (inside visible)
    ctx.set_source_rgb(0.10, 0.01, 0.01)
    ctx.move_to(-114, -72); ctx.curve_to(-90, -80, -60, -74, -40, -64); ctx.curve_to(-22, -54, -2, -50, 10, -52)
    ctx.curve_to(-20, -40, -80, -46, -114, -72); ctx.fill()
    # sole
    ctx.set_source_rgb(*dark); ctx.set_line_width(7)
    ctx.move_to(-124, 2); ctx.curve_to(-40, 10, 60, 12, 156, 5); ctx.stroke()
    # strap + buckle
    ctx.set_source_rgb(col[0] * 0.6, col[1] * 0.4, col[2] * 0.4); ctx.set_line_width(11)
    ctx.move_to(-62, -74); ctx.curve_to(-58, -90, -40, -96, -30, -62); ctx.stroke()
    ctx.set_source_rgb(0.85, 0.68, 0.35); ctx.set_line_width(4); ctx.rectangle(-46, -98, 16, 14); ctx.stroke()
    # highlight
    ctx.set_source_rgba(1, 0.85, 0.8, 0.4); ctx.set_line_width(4)
    ctx.move_to(20, -48); ctx.curve_to(70, -50, 120, -34, 150, -18); ctx.stroke()
    ctx.move_to(-124, -40); ctx.curve_to(-122, -58, -118, -66, -110, -72); ctx.stroke()
    ctx.restore()

def musician(ctx, x, y, s, t, kind):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.set_source_rgb(*SIL)
    b = math.sin(t * 9) * 4
    limb(ctx, [(-12, 0), (-14, -50), (-10, -95)], 13); limb(ctx, [(12, 0), (14, -50), (10, -95)], 13)
    limb(ctx, [(0, -95), (0 + b * 0.3, -160)], 32)
    ctx.arc(b * 0.5, -185, 18, 0, 2 * math.pi); ctx.fill()
    ctx.move_to(-26, -195); ctx.line_to(26, -195); ctx.line_to(b * 0.5, -235); ctx.fill()  # hat
    if kind == 'fiddle':
        ctx.save(); ctx.translate(-20, -165); ctx.rotate(-0.5); ctx.scale(34, 14); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
        limb(ctx, [(-5, -150), (-40, -160)], 9)
        bx = math.sin(t * 9) * 30
        limb(ctx, [(10, -150), (30 + bx * 0.4, -140)], 9)
        ctx.set_line_width(3); ctx.move_to(-10 + bx, -200); ctx.line_to(30 + bx, -120); ctx.stroke()
    else:
        ctx.save(); ctx.translate(0, -110); ctx.scale(42, 34); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
        hit = abs(math.sin(t * 4.5 * math.pi / 2))
        limb(ctx, [(10, -150), (40, -150 + hit * 20), (60, -160 + hit * 40)], 9)
        limb(ctx, [(-10, -150), (-40, -140), (-30, -130)], 9)
    ctx.restore()

def lantern(ctx, x, y, t, k):
    fl = 0.85 + 0.15 * math.sin(t * 13 + k * 2.1) * math.sin(t * 7.3 + k)
    g = cairo.RadialGradient(x, y, 3, x, y, 160)
    g.add_color_stop_rgba(0, 1, 0.7, 0.3, 0.5 * fl); g.add_color_stop_rgba(1, 1, 0.6, 0.25, 0)
    ctx.set_source(g); ctx.arc(x, y, 160, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(1, 0.78, 0.4); ctx.arc(x, y, 9, 0, 2 * math.pi); ctx.fill()

# ---------------- crowd layout ----------------
def crowd_layout(n, seed=1, y0=1360, y1=1700):
    rng = random.Random(seed); out = []
    for i in range(n):
        d = rng.random()
        y = y0 + (y1 - y0) * d ** 0.8
        s = 0.5 + 0.8 * (y - y0) / (y1 - y0)
        x = rng.uniform(40, W - 40)
        out.append((x, y, s, rng.uniform(0, 6.28), rng.random() < 0.6, rng.uniform(0.8, 1.35)))
    out.sort(key=lambda p: p[1])
    return out
CROWD = crowd_layout(70)
CROWD_E = sorted([(110 + (i % 6) * 172 + (i // 6) * 60 % 172 - 40, 1420 + (i // 6) * 110, 0.75 + (i // 6) * 0.22, i * 1.3, i % 3 != 0, 1.0 + (i % 4) * 0.1) for i in range(18)], key=lambda p: p[1])

# ---------------- scene draw functions (t = global time) ----------------
STREET = None; LAND = None

def scene_A(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, STREET, lt, 1.0, 1.10, e - s)
    rise = ease(lt / 1.2)
    dancer(ctx, W / 2, 1640, 2.1 * (0.9 + 0.1 * rise), t, 0.0, speed=0.55 + 0.4 * ease((t - ps(1)) / 1.0), frenzy=0.25 + 0.75 * ease((t - ps(1)) / 1.2))
    fog(ctx, 1650, 120, 0.12)
    a = ease(lt / 0.6) * (1 - ease((lt - (e - s - 0.6)) / 0.5))
    title(ctx, 'STRASBOURG', 520, 92, a, spacing=10)
    title(ctx, '1518', 650, 120, a, col=(0.85, 0.12, 0.15))

def scene_B(ctx, t, s, e):
    lt = t - s
    z = bg_paint(ctx, STREET, lt, 1.35, 1.5, e - s, dy=-120)
    dancer(ctx, W / 2, 1880, 4.4 + 0.3 * ease(lt / (e - s)), t, 0.4, speed=1.25, frenzy=1.25)
    # red pulse on "could not stop"
    k = ease((t - ps(4)) / 0.4)
    vignette(ctx, 0.55 * k, col=(0.5, 0, 0.02))

def scene_C(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, STREET, lt, 1.06, 1.0, e - s)
    # number of dancers ramps: dozens then hundreds
    n1 = 4 + int(26 * ease((t - s) / max(0.1, ps(6) - s)))
    n2 = int(40 * ease((t - ps(6)) / 2.0))
    n = min(len(CROWD), n1 + n2)
    for (x, y, sc, ph, dr, sp) in CROWD[-n:] if n > 0 else []:
        dancer(ctx, x, y, sc, t, ph, dress=dr, speed=sp, frenzy=1.0)
    if t > ps(6):
        k = ease((t - ps(6)) / 1.6)
        num = int(400 * k)
        a = ease((t - ps(6)) / 0.3)
        title(ctx, f'{num}', 560, 230, a, font='Anton', col=(0.85, 0.12, 0.15))
        title(ctx, 'DANCERS', 650, 64, a)

def stage(ctx, t):
    # platform
    ctx.set_source_rgb(0.05, 0.04, 0.04)
    ctx.rectangle(80, 1460, W - 160, 50); ctx.fill()
    for px in range(110, W - 100, 140): ctx.rectangle(px, 1500, 18, 160); ctx.fill()
    ctx.rectangle(110, 1040, 16, 430); ctx.fill(); ctx.rectangle(W - 126, 1040, 16, 430); ctx.fill()
    # bunting
    ctx.set_line_width(4); ctx.move_to(118, 1060); ctx.curve_to(400, 1160, 680, 1160, W - 118, 1060); ctx.stroke()
    for i in range(1, 12):
        u = i / 12; bx = 118 + u * (W - 236); by = 1060 + math.sin(u * math.pi) * 75
        ctx.set_source_rgb(*(RED if i % 2 else (0.15, 0.12, 0.1)))
        ctx.move_to(bx - 18, by); ctx.line_to(bx + 18, by); ctx.line_to(bx, by + 40); ctx.fill()

def scene_D(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, STREET, lt, 1.0, 1.08, e - s)
    show_stage = ease((t - ps(8) + 0.1) / 0.5) if t > ps(8) - 0.1 else 0
    show_mus = t > ps(9) - 0.1
    if t < ps(8) - 0.1:
        # council: robed figures standing, still
        for i, x in enumerate([300, 450, 630, 780]):
            ctx.save(); ctx.set_source_rgb(*SIL)
            ctx.move_to(x - 55, 1700); ctx.line_to(x - 30, 1420); ctx.line_to(x + 30, 1420); ctx.line_to(x + 55, 1700); ctx.fill()
            ctx.arc(x, 1390, 30, 0, 2 * math.pi); ctx.fill()
            ctx.rectangle(x - 34, 1340, 68, 26); ctx.fill(); ctx.restore()
        title(ctx, 'THE CITY COUNCIL', 560, 70, ease(lt / 0.4))
        return
    ctx.save(); ctx.translate(0, (1 - show_stage) * 500)
    stage(ctx, t)
    for k, lx in enumerate([180, 540, 900]): lantern(ctx, lx, 1110 + (k == 1) * 40, t, k)
    if show_mus:
        musician(ctx, 230, 1460, 1.15, t, 'fiddle'); musician(ctx, 860, 1460, 1.15, t, 'drum')
    for i, (x, sc, ph) in enumerate([(430, 1.25, 0.2), (560, 1.3, 2.0), (690, 1.2, 4.0)]):
        dancer(ctx, x, 1460, sc, t, ph, dress=i != 1, speed=1.1)
    ctx.restore()
    for (x, y, sc, ph, dr, sp) in CROWD[-22:]:
        if y > 1650: dancer(ctx, x, y + 60, sc * 1.1, t, ph, dress=dr, speed=sp)
    fog(ctx, 1750, 140, 0.15)

def scene_E(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, STREET, lt, 1.0, 1.12, e - s)
    rng = random.Random(4)
    for i, (x, y, sc, ph, dr, sp) in enumerate(CROWD_E):
        cstart = ps(12) - 0.3 + rng.uniform(0, 2.6)
        col = ease((t - cstart) / 0.7)
        dancer(ctx, x, y, sc, t, ph, dress=dr, speed=sp * (1 - 0.6 * col), collapse=col, frenzy=1.2 - 0.9 * col)
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    vignette(ctx, 0.45 + 0.2 * pulse * ease((t - ps(12)) / 1), col=(0.45, 0, 0.02))

def scene_F(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, LAND, lt, 1.0, 1.06, e - s)
    u = ease(lt / (e - s))
    # wagon follows the road toward the hill
    x = -100 + u * 520; y = 1590 - u * 190; sc = 1.7 - u * 0.75
    wagon(ctx, x, y, sc, t)
    if t > ps(14) - 0.1:
        a = ease((t - ps(14)) / 0.5)
        title(ctx, 'SAINT VITUS', 560, 84, a)
        title(ctx, 'the saint they blamed', 640, 44, a, col=(0.8, 0.75, 0.65))

def scene_S(ctx, t, s, e):
    lt = t - s
    ctx.set_source_rgb(0.03, 0.025, 0.025); ctx.paint()
    ground(ctx, 700, col=(0.02, 0.02, 0.02))
    g = cairo.RadialGradient(W / 2, 1360, 30, W / 2, 1360, 620)
    g.add_color_stop_rgba(0, 1, 0.9, 0.75, 0.30); g.add_color_stop_rgba(1, 1, 0.9, 0.75, 0)
    ctx.set_source(g); ctx.paint()
    z = 1.0 + 0.12 * ease(lt / (e - s))
    ctx.save(); ctx.translate(W / 2, 1360); ctx.scale(z, z)
    ctx.set_source_rgba(0, 0, 0, 0.5); ctx.save(); ctx.scale(380, 60); ctx.arc(0, 2.3, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    shoe(ctx, -70, -60, 1.7, 1); shoe(ctx, 60, 120, 1.7, 1)
    ctx.restore()

def scene_G(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, STREET, lt, 1.0, 1.18, e - s, dy=-40)
    sh = 0.55
    ctx.save(); ctx.translate(W / 2, 1600)
    shoe(ctx, -10, -30, sh, 1); shoe(ctx, 15, 35, sh, 1); ctx.restore()
    fog(ctx, 1620, 130, 0.15)
    if t > ps(18) - 0.1:
        # a lone shadow sways at the end
        a = ease((t - ps(18)) / 0.8)
        dancer(ctx, W / 2 + 280, 1560, 1.5, t, 1.0, col=(0.02 * a + 0.13 * (1 - a),) * 3, speed=0.7, frenzy=0.6 * a)

DRAW = {'A': scene_A, 'B': scene_B, 'C': scene_C, 'D': scene_D, 'E': scene_E, 'F': scene_F, 'S': scene_S, 'G': scene_G}

def frame(ctx, name, t, s, e):
    ctx.save(); DRAW[name](ctx, t, s, e); ctx.restore()
    vignette(ctx, 0.8)
    # candle flicker
    fl = 0.04 * (math.sin(t * 17) * math.sin(t * 5.3) + 1)
    ctx.set_source_rgba(0, 0, 0, fl); ctx.paint()
    # cut flash-in
    k = t - s
    if k < 0.15 and name != 'A': ctx.set_source_rgba(0, 0, 0, 1 - k / 0.15); ctx.paint()
    if name == 'A' and k < 0.4: ctx.set_source_rgba(0, 0, 0, 1 - k / 0.4); ctx.paint()
    draw_captions(ctx, t)

def render_scene(idx, out_dir=None):
    out_dir = out_dir or EP + '/out'
    global STREET, LAND
    STREET = street_bg(); LAND = landscape_bg()
    name, s, e = scene_bounds()[idx]
    n0 = round(s * FPS); n1 = round(e * FPS)
    os.makedirs(out_dir, exist_ok=True)
    tmp = f'{out_dir}/{idx:02d}_{name}.tmp.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-vf', 'noise=alls=10:allf=t,format=yuv420p', '-c:v', 'libx264', '-crf', '19', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp],
                         stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    for n in range(n0, n1):
        ctx = cairo.Context(surf)
        ctx.set_source_rgb(0, 0, 0); ctx.paint()
        frame(ctx, name, n / FPS, s, e)
        surf.flush()
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.replace(tmp, tmp.replace('.tmp.mp4', '.mp4'))
    return rc

def still(t, path):
    global STREET, LAND
    STREET = street_bg(); LAND = landscape_bg()
    for name, s, e in scene_bounds():
        if s <= t < e: break
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
    ctx.set_source_rgb(0, 0, 0); ctx.paint(); frame(ctx, name, t, s, e); surf.write_to_png(path)

if __name__ == '__main__':
    if sys.argv[1] == 'still':
        for t in sys.argv[2:]: still(float(t), f'{EP}/stills/f_{float(t):05.1f}.png')
    else:
        sys.exit(render_scene(int(sys.argv[1])))
