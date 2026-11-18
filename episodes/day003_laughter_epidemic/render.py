import cairo, math, json, random, subprocess, sys, os
W, H, FPS = 1080, 1920, 30
EP = os.environ['EP']
TIM = json.load(open(EP + '/timing.json'))
RED = (0.80, 0.07, 0.12)
SIL = (0.02, 0.02, 0.03)

def ps(i): return TIM[i]['start']

SCENES = [('A', 0), ('B', 1), ('C', 2), ('D', 4), ('E', 5), ('F', 7), ('G', 8), ('H', 10), ('I', 12), ('J', 14), ('K', 15), ('L', 16)]
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

def bg_paint(ctx, surf, t, z0, z1, dur, dx=0, dy=0):
    z = z0 + (z1 - z0) * ease(t / dur) if dur > 0 else z0
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2 + dx, -H / 2 + dy)
    ctx.set_source_surface(surf, -100, -100); ctx.paint(); ctx.restore()
    return z

def lantern(ctx, x, y, t, k):
    fl = 0.85 + 0.15 * math.sin(t * 13 + k * 2.1) * math.sin(t * 7.3 + k)
    g = cairo.RadialGradient(x, y, 3, x, y, 160)
    g.add_color_stop_rgba(0, 1, 0.7, 0.3, 0.5 * fl); g.add_color_stop_rgba(1, 1, 0.6, 0.25, 0)
    ctx.set_source(g); ctx.arc(x, y, 160, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(1, 0.78, 0.4); ctx.arc(x, y, 9, 0, 2 * math.pi); ctx.fill()


# ================= Day 3: Tanganyika laughter epidemic =================
AMBER = (0.95, 0.62, 0.25)

def glow(ctx, x, y, r, a=0.5, col=(0.95, 0.62, 0.25)):
    g = cairo.RadialGradient(x, y, 2, x, y, r)
    g.add_color_stop_rgba(0, *col, a); g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

def lake(ctx, y0, y1, mx):
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgb(0, 0.30, 0.24, 0.20); g.add_color_stop_rgb(1, 0.10, 0.09, 0.10)
    ctx.set_source(g); ctx.rectangle(0, y0, W, y1 - y0); ctx.fill()
    rng = random.Random(11)
    for i in range(26):
        y = y0 + 6 + (i ** 1.3) * 3.2
        if y > y1: break
        w = rng.uniform(40, 160) * (1 - 0.5 * (y - y0) / (y1 - y0))
        ctx.set_source_rgba(0.95, 0.86, 0.68, 0.45 - 0.012 * i)
        ctx.rectangle(mx - w / 2 + rng.uniform(-30, 30), y, w, 3); ctx.fill()

def acacia(ctx, x, base, s, col=SIL):
    ctx.save(); ctx.translate(x, base); ctx.scale(s, s); ctx.set_source_rgb(*col)
    limb(ctx, [(0, 0), (4, -150), (-50, -260)], 14); limb(ctx, [(4, -150), (60, -250)], 12); limb(ctx, [(2, -190), (10, -275)], 9)
    for cx, cy, rx, ry in [(-60, -270, 120, 26), (70, -262, 130, 24), (5, -292, 110, 22)]:
        ctx.save(); ctx.translate(cx, cy); ctx.scale(rx, ry); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    ctx.restore()

def banana(ctx, x, base, s, col=SIL, t=0):
    ctx.save(); ctx.translate(x, base); ctx.scale(s, s); ctx.set_source_rgb(*col)
    ctx.move_to(-12, 0); ctx.line_to(-7, -170); ctx.line_to(7, -170); ctx.line_to(12, 0); ctx.fill()
    for k, (ang, ln) in enumerate([(-2.3, 150), (-1.8, 170), (-1.2, 160), (-0.7, 150), (-2.7, 120), (-0.35, 120)]):
        a = ang + 0.04 * math.sin(t * 1.3 + k)
        ex, ey = math.cos(a) * ln, -170 + math.sin(a) * ln * 0.75 + 40
        mx, my = math.cos(a) * ln * 0.5, -170 + math.sin(a) * ln * 0.75 - 25
        ctx.move_to(0, -168); ctx.curve_to(mx, my - 22, ex, ey - 22, ex, ey)
        ctx.curve_to(ex, ey + 6, mx, my + 18, 0, -160); ctx.fill()
    ctx.restore()

def hut(ctx, x, base, s, lit=True, col=SIL, t=0, k=0):
    ctx.save(); ctx.translate(x, base); ctx.scale(s, s); ctx.set_source_rgb(*col)
    ctx.rectangle(-60, -80, 120, 80); ctx.fill()
    ctx.move_to(-85, -72); ctx.line_to(0, -175); ctx.line_to(85, -72); ctx.fill()
    if lit:
        fl = 0.85 + 0.15 * math.sin(t * 11 + k)
        glow(ctx, 0, -32, 70, 0.4 * fl)
        ctx.set_source_rgb(*AMBER); ctx.move_to(-14, 0); ctx.line_to(-14, -40); ctx.arc(0, -40, 14, math.pi, 0); ctx.line_to(14, 0); ctx.fill()
    ctx.restore()

def bell(ctx, x, y, s, ang=0.0):
    """Red hand-bell hanging from (x,y)."""
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.scale(s, s)
    ctx.set_source_rgb(0.25, 0.2, 0.15); ctx.rectangle(-4, 0, 8, 14); ctx.fill()
    g = cairo.LinearGradient(-40, 0, 40, 0)
    g.add_color_stop_rgb(0, 0.45, 0.03, 0.06); g.add_color_stop_rgb(0.4, 0.95, 0.2, 0.22); g.add_color_stop_rgb(1, 0.35, 0.02, 0.05)
    ctx.move_to(-10, 14); ctx.curve_to(-26, 18, -28, 50, -32, 70); ctx.curve_to(-36, 80, -44, 82, -44, 88)
    ctx.line_to(44, 88); ctx.curve_to(44, 82, 36, 80, 32, 70); ctx.curve_to(28, 50, 26, 18, 10, 14); ctx.close_path()
    ctx.set_source(g); ctx.fill()
    ctx.set_source_rgb(0.3, 0.02, 0.04); ctx.arc(0, 92, 9, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def school(ctx, x, base, s, t=0, swing=0.0, lit=0.9):
    """Mission boarding school: long low building, tin roof, veranda, belfry with red bell."""
    ctx.save(); ctx.translate(x, base); ctx.scale(s, s)
    ctx.set_source_rgb(*SIL)
    ctx.rectangle(-380, -170, 760, 170); ctx.fill()
    ctx.move_to(-410, -160); ctx.line_to(-340, -250); ctx.line_to(340, -250); ctx.line_to(410, -160); ctx.fill()
    ctx.set_source_rgba(0.3, 0.26, 0.22, 0.5); ctx.set_line_width(2)
    for i in range(-330, 340, 22): ctx.move_to(i, -248); ctx.line_to(i * 1.2, -162); ctx.stroke()
    ctx.set_source_rgb(*SIL)
    # gable with cross
    ctx.move_to(-90, -250); ctx.line_to(0, -330); ctx.line_to(90, -250); ctx.fill()
    ctx.rectangle(-4, -390, 8, 64); ctx.fill(); ctx.rectangle(-22, -372, 44, 8); ctx.fill()
    # belfry on the right
    bx = 300
    ctx.rectangle(bx - 8, -440, 16, 200); ctx.fill(); ctx.rectangle(bx + 92, -440, 16, 200); ctx.fill()
    ctx.move_to(bx - 30, -440); ctx.line_to(bx + 50, -500); ctx.line_to(bx + 130, -440); ctx.fill()
    bell(ctx, bx + 50, -438, 0.8, swing)
    # windows
    rng = random.Random(7)
    for wx in [-330, -250, -170, 130, 210]:
        if rng.random() < lit:
            fl = 0.85 + 0.15 * math.sin(t * 9 + wx)
            glow(ctx, wx + 20, -95, 80, 0.35 * fl)
            ctx.set_source_rgb(*AMBER); ctx.rectangle(wx, -125, 40, 56); ctx.fill()
            ctx.set_source_rgb(*SIL); ctx.rectangle(wx + 19, -125, 3, 56); ctx.fill(); ctx.rectangle(wx, -99, 40, 3); ctx.fill()
    # door
    ctx.set_source_rgb(0.18, 0.12, 0.08); ctx.rectangle(-40, -150, 80, 150); ctx.fill()
    ctx.restore()

def girl(ctx, x, y, s, t, ph, laugh=0.0, collapse=0.0, walk=0.0, col=SIL, sit=False):
    """Schoolgirl silhouette, feet at (x,y), height ~200*s. laugh 0..1 = shaking fit."""
    ctx.save(); ctx.translate(x, y)
    if collapse > 0:
        c = ease(collapse); ctx.rotate((1 if math.sin(ph * 7) > 0 else -1) * c * 1.4)
    ctx.scale(s, s); ctx.set_source_rgb(*col)
    sh = math.sin(t * 2 * math.pi * 4.6 + ph) * laugh          # fast shake
    heave = math.sin(t * 2 * math.pi * 1.1 + ph) * laugh      # slow heave
    a = t * 2 * math.pi * 1.0 + ph
    hip = (sh * 2, -92 - abs(sh) * 4 - heave * 3)
    lean = -0.05 + 0.18 * laugh * (0.5 + 0.5 * heave)          # lean back/forward
    neck = (hip[0] + math.sin(lean) * 64, hip[1] - math.cos(lean) * 64)
    tilt = -0.35 * laugh * (0.5 + 0.5 * heave) + 0.12 * sh
    head = (neck[0] - math.sin(tilt) * 22, neck[1] - math.cos(tilt) * 22)
    for side in (-1, 1):
        sw = math.sin(a + (0 if side > 0 else math.pi)) * walk
        knee = (hip[0] + side * 9 + sw * 14, hip[1] + 48)
        foot = (hip[0] + side * 11 + sw * 30, 0 - max(0, sw) * 8)
        limb(ctx, [hip, knee, foot], 12)
    limb(ctx, [hip, neck], 28)
    # school dress
    ctx.move_to(hip[0] - 14, hip[1] - 22); ctx.line_to(hip[0] + 14, hip[1] - 22)
    ctx.line_to(hip[0] + 36 + sh * 3, hip[1] + 52); ctx.line_to(hip[0] - 36 + sh * 3, hip[1] + 52); ctx.close_path(); ctx.fill()
    # arms
    shL = (neck[0] - 12, neck[1] + 8); shR = (neck[0] + 12, neck[1] + 8)
    if laugh > 0.3:
        limb(ctx, [shL, (shL[0] - 16, shL[1] + 34), (hip[0] - 2, hip[1] - 8 + sh * 3)], 9)       # clutching belly
        limb(ctx, [shR, (shR[0] + 26, shR[1] + 18), (head[0] + 10, head[1] + 12 + sh * 2)], 9)  # hand to mouth
    else:
        sw = math.sin(a) * walk
        limb(ctx, [shL, (shL[0] - 6 - sw * 10, shL[1] + 36), (shL[0] - 4 - sw * 18, shL[1] + 70)], 9)
        limb(ctx, [shR, (shR[0] + 6 + sw * 10, shR[1] + 36), (shR[0] + 4 + sw * 18, shR[1] + 70)], 9)
    ctx.arc(head[0], head[1], 17, 0, 2 * math.pi); ctx.fill()
    ctx.arc(head[0] - 3, head[1] - 7, 15, 0, 2 * math.pi); ctx.fill()   # short hair
    ctx.restore()

def desk(ctx, x, y, w):
    ctx.set_source_rgb(0.035, 0.03, 0.03)
    ctx.rectangle(x - w / 2, y, w, 22); ctx.fill()
    ctx.rectangle(x - w / 2, y + 22, w, 120); ctx.fill()

def clock(ctx, x, y, r, t, spin):
    ctx.set_source_rgba(0.93, 0.87, 0.74, 0.92); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(*SIL); ctx.set_line_width(10); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.stroke()
    for k in range(12):
        an = k * math.pi / 6
        ctx.set_line_width(6 if k % 3 == 0 else 3)
        ctx.move_to(x + math.cos(an) * r * 0.8, y + math.sin(an) * r * 0.8); ctx.line_to(x + math.cos(an) * r * 0.92, y + math.sin(an) * r * 0.92); ctx.stroke()
    m = spin; h = spin / 12
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(12); ctx.move_to(x, y); ctx.line_to(x + math.sin(h) * r * 0.5, y - math.cos(h) * r * 0.5); ctx.stroke()
    ctx.set_source_rgb(*RED); ctx.set_line_width(7); ctx.move_to(x, y); ctx.line_to(x + math.sin(m) * r * 0.78, y - math.cos(m) * r * 0.78); ctx.stroke()
    ctx.set_source_rgb(*SIL); ctx.arc(x, y, 10, 0, 2 * math.pi); ctx.fill()

def profile_head(ctx, x, y, s, flip=1, col=SIL):
    ctx.save(); ctx.translate(x, y); ctx.scale(s * flip, s); ctx.set_source_rgb(*col)
    ctx.move_to(-60, 180); ctx.line_to(-55, 60)
    ctx.curve_to(-110, 20, -110, -120, -20, -140)
    ctx.curve_to(50, -150, 90, -100, 92, -40)
    ctx.line_to(112, 0); ctx.line_to(92, 10); ctx.line_to(96, 30); ctx.line_to(88, 40)
    ctx.curve_to(96, 52, 90, 70, 60, 74); ctx.line_to(40, 80); ctx.line_to(36, 180); ctx.close_path(); ctx.fill()
    ctx.restore()

# ---------------- cached backgrounds ----------------
def mk():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(100, 100); return surf, ctx

def savanna_bg():
    surf, ctx = mk()
    sky(ctx, top=(0.04, 0.05, 0.08), bot=(0.36, 0.24, 0.16), horizon=1240); moon(ctx, 800, 780, 60)
    ctx.set_source_rgb(0.12, 0.09, 0.09); ctx.move_to(-100, 1240)
    for i in range(-100, W + 200, 40): ctx.line_to(i, 1215 - 25 * math.sin(i / 140) - 12 * math.sin(i / 47))
    ctx.line_to(W + 100, 1250); ctx.fill()
    lake(ctx, 1240, 1420, 800)
    ground(ctx, 1410)
    acacia(ctx, 180, 1450, 1.25, (0.03, 0.03, 0.04)); acacia(ctx, 930, 1440, 0.8, (0.05, 0.045, 0.05))
    for bx, s in [(40, 1.5), (1050, 1.7)]: banana(ctx, bx, 1900, s)
    fog(ctx, 1400, 110, 0.18)
    return surf

def school_bg():
    surf, ctx = mk()
    sky(ctx, top=(0.04, 0.05, 0.08), bot=(0.32, 0.22, 0.16), horizon=1300); moon(ctx, 170, 640, 54)
    lake(ctx, 1260, 1330, 170)
    ground(ctx, 1320)
    acacia(ctx, 960, 1360, 0.9, (0.06, 0.05, 0.06))
    return surf

def room_bg():
    surf, ctx = mk()
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.10, 0.08, 0.07); g.add_color_stop_rgb(0.7, 0.20, 0.15, 0.11); g.add_color_stop_rgb(1, 0.06, 0.05, 0.05)
    ctx.set_source(g); ctx.rectangle(-100, -100, W + 200, H + 200); ctx.fill()
    # window with moon + bars
    wx, wy, ww, wh = 360, 300, 360, 460
    g = cairo.LinearGradient(0, wy, 0, wy + wh); g.add_color_stop_rgb(0, 0.12, 0.13, 0.17); g.add_color_stop_rgb(1, 0.34, 0.26, 0.2)
    ctx.set_source(g); ctx.rectangle(wx, wy, ww, wh); ctx.fill()
    moon(ctx, wx + 240, wy + 130, 46)
    ctx.set_source_rgb(*SIL); ctx.set_line_width(14); ctx.rectangle(wx, wy, ww, wh); ctx.stroke()
    ctx.set_line_width(8)
    for k in range(1, 4): ctx.move_to(wx + k * ww / 4, wy); ctx.line_to(wx + k * ww / 4, wy + wh); ctx.stroke()
    ctx.move_to(wx, wy + wh / 2); ctx.line_to(wx + ww, wy + wh / 2); ctx.stroke()
    # moonbeam
    ctx.set_source_rgba(0.95, 0.88, 0.72, 0.07); ctx.move_to(wx, wy + wh); ctx.line_to(wx + ww, wy + wh); ctx.line_to(wx + ww + 300, H); ctx.line_to(wx - 200, H); ctx.fill()
    # blackboard edge left, crucifix right
    ctx.set_source_rgb(0.05, 0.05, 0.05); ctx.rectangle(-100, 360, 330, 360); ctx.fill()
    ctx.set_source_rgb(*SIL); ctx.rectangle(890, 420, 10, 90); ctx.fill(); ctx.rectangle(870, 445, 50, 9); ctx.fill()
    ctx.set_source_rgb(0.08, 0.06, 0.05); ctx.rectangle(-100, 1500, W + 200, 600); ctx.fill()
    return surf

def road_bg():
    surf, ctx = mk()
    sky(ctx, top=(0.04, 0.05, 0.08), bot=(0.34, 0.22, 0.15), horizon=1180); moon(ctx, 820, 380, 52)
    ctx.set_source_rgb(0.10, 0.08, 0.09); ctx.move_to(-100, 1180)
    for i in range(-100, W + 200, 40): ctx.line_to(i, 1120 - 50 * math.sin(i / 190) - 20 * math.sin(i / 70))
    ctx.line_to(W + 100, H); ctx.line_to(-100, H); ctx.fill()
    ground(ctx, 1200)
    ctx.set_source_rgba(0.45, 0.35, 0.27, 0.4)
    ctx.move_to(-100, 1780); ctx.curve_to(300, 1700, 500, 1350, 760, 1215); ctx.line_to(790, 1215); ctx.curve_to(560, 1380, 420, 1760, -100, 1900); ctx.fill()
    for hx, s in [(760, 0.55), (880, 0.48), (960, 0.6)]: hut(ctx, hx, 1215, s, t=0)
    banana(ctx, 1010, 1600, 1.3); banana(ctx, 80, 1500, 1.0, (0.04, 0.035, 0.04)); acacia(ctx, 300, 1230, 0.6, (0.07, 0.06, 0.06))
    fog(ctx, 1210, 90, 0.2)
    return surf

def map_bg():
    surf, ctx = mk()
    g = cairo.RadialGradient(W / 2, H * 0.45, 100, W / 2, H * 0.45, 1100)
    g.add_color_stop_rgb(0, 0.36, 0.28, 0.19); g.add_color_stop_rgb(1, 0.11, 0.08, 0.06)
    ctx.set_source(g); ctx.rectangle(-100, -100, W + 200, H + 200); ctx.fill()
    rng = random.Random(3)
    for _ in range(600):
        ctx.set_source_rgba(0.1, 0.07, 0.04, rng.uniform(0.03, 0.12)); ctx.arc(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(2, 14), 0, 2 * math.pi); ctx.fill()
    # Lake Victoria (stylised) on the right; Kashasha on its western shore
    pts = [(560, 240), (760, 200), (980, 260), (1140, 330), (1180, 700), (1160, 1500), (900, 1560), (720, 1480), (640, 1300), (600, 1120), (640, 940), (610, 760), (640, 600), (560, 420)]
    ctx.move_to(*pts[0])
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]; x1, y1 = pts[i]
        ctx.curve_to(x0 + (x1 - x0) * 0.3 + 20, y0 + (y1 - y0) * 0.3, x0 + (x1 - x0) * 0.7 - 20, y0 + (y1 - y0) * 0.7, x1, y1)
    ctx.close_path()
    ctx.set_source_rgba(0.08, 0.09, 0.11, 0.85); ctx.fill_preserve()
    ctx.set_source_rgba(0.93, 0.87, 0.74, 0.5); ctx.set_line_width(4); ctx.stroke()
    ctx.select_font_face('Cinzel', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(40)
    ctx.set_source_rgba(0.93, 0.87, 0.74, 0.55)
    for i, w in enumerate(['LAKE', 'VICTORIA']):
        ctx.move_to(800, 1300 + i * 50); ctx.show_text(w)
    # dotted tracks
    ctx.set_source_rgba(0.93, 0.87, 0.74, 0.35); ctx.set_line_width(4); ctx.set_dash([10, 12])
    for a, b in [((560, 820), (300, 520)), ((560, 820), (260, 1280)), ((560, 820), (180, 860)), ((260, 1280), (420, 1500))]:
        ctx.move_to(*a); ctx.line_to(*b); ctx.stroke()
    ctx.set_dash([])
    return surf

def calendar_bg():
    surf, ctx = mk()
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.08, 0.065, 0.06); g.add_color_stop_rgb(1, 0.22, 0.16, 0.12)
    ctx.set_source(g); ctx.rectangle(-100, -100, W + 200, H + 200); ctx.fill()
    return surf

BG = {}

def road_pt(u):
    P = [(-100, 1840), (300, 1740), (500, 1370), (775, 1215)]
    a = (1 - u) ** 3; b = 3 * u * (1 - u) ** 2; c = 3 * u * u * (1 - u); d = u ** 3
    return (a * P[0][0] + b * P[1][0] + c * P[2][0] + d * P[3][0], a * P[0][1] + b * P[1][1] + c * P[2][1] + d * P[3][1])

def doctor(ctx, x, y, s, t):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.set_source_rgb(*SIL)
    limb(ctx, [(-12, 0), (-12, -95)], 14); limb(ctx, [(12, 0), (12, -95)], 14)
    ctx.move_to(-34, -80); ctx.line_to(-26, -175); ctx.line_to(26, -175); ctx.line_to(34, -80); ctx.fill()   # coat
    lean = 0.04 * math.sin(t * 0.8)
    limb(ctx, [(20, -165), (55, -135), (88 + 4 * math.sin(t * 2), -128)], 10)
    limb(ctx, [(-20, -165), (-30, -125), (-14, -100)], 10)
    ctx.arc(4 + lean * 60, -200, 20, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(0.93, 0.87, 0.74, 0.8); ctx.arc(8 + lean * 60, -214, 7, 0, 2 * math.pi); ctx.fill()   # head mirror glint
    ctx.restore()

def microscope(ctx, x, y, s):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.set_source_rgb(*SIL)
    ctx.rectangle(-45, -12, 90, 12); ctx.fill()
    limb(ctx, [(-20, -10), (-28, -60), (-10, -110)], 14)
    ctx.save(); ctx.translate(5, -100); ctx.rotate(0.35); ctx.rectangle(-10, -60, 20, 80); ctx.restore(); ctx.fill()
    ctx.rectangle(-30, -48, 60, 8); ctx.fill()
    ctx.restore()

def tubes(ctx, x, y, s, fill=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    ctx.set_source_rgb(*SIL); ctx.rectangle(-70, -40, 140, 12); ctx.fill(); ctx.rectangle(-70, -4, 140, 8); ctx.fill()
    for k in range(5):
        tx = -56 + k * 28
        ctx.set_source_rgba(0.93, 0.87, 0.74, 0.35); ctx.rectangle(tx, -90, 14, 86); ctx.fill()
        ctx.set_source_rgba(0.95, 0.62, 0.25, 0.85); ctx.rectangle(tx + 2, -4 - 40 * fill, 10, 40 * fill); ctx.fill()
    ctx.restore()

def strike(ctx, text, y, size, k):
    ctx.select_font_face('Cinzel', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
    ex = ctx.text_extents(text); x0 = W / 2 - ex.x_advance / 2 - 10
    ctx.set_source_rgb(*RED); ctx.set_line_width(10); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(x0, y - size * 0.32); ctx.line_to(x0 + (ex.x_advance + 20) * k, y - size * 0.32); ctx.stroke()

def dark_floor(ctx, y=1450):
    g = cairo.LinearGradient(0, y, 0, H); g.add_color_stop_rgb(0, 0.14, 0.10, 0.08); g.add_color_stop_rgb(1, 0.03, 0.03, 0.03)
    ctx.set_source(g); ctx.rectangle(0, y, W, H - y); ctx.fill()

# ---------------- scene draw functions (t = global time) ----------------
def scene_A(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['sav'], lt, 1.0, 1.10, e - s)
    for i in range(3):
        girl(ctx, 330 + i * 70 + lt * 14, 1500, 0.42, t, i * 1.7, walk=1.0)
    a = ease(lt / 0.6) * (1 - ease((lt - (e - s - 0.6)) / 0.5))
    title(ctx, 'TANGANYIKA', 440, 96, a)
    title(ctx, '1962', 590, 130, a, col=(0.85, 0.12, 0.15))
    title(ctx, 'EAST AFRICA', 680, 44, a * 0.9, col=(0.8, 0.75, 0.65))

def scene_B(ctx, t, s, e):
    lt = t - s
    z = 1.0 + 0.08 * ease(lt / (e - s))
    bg_paint(ctx, BG['school'], lt, 1.0, 1.08, e - s)
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2)
    school(ctx, W / 2, 1310, 1.15, t, swing=0.06 * math.sin(t * 1.5))
    banana(ctx, 60, 1520, 1.4, t=t); banana(ctx, 1030, 1560, 1.2, t=t)
    ctx.restore()
    fog(ctx, 1330, 110, 0.2)
    a = ease(lt / 0.5)
    title(ctx, 'KASHASHA', 330, 84, a)
    title(ctx, "mission boarding school for girls", 400, 38, a, col=(0.8, 0.75, 0.65))

def scene_C(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['room'], lt, 1.0, 1.12, e - s, dy=-30)
    lantern(ctx, 920, 640, t, 1)
    k3 = ease((t - ps(3)) / 0.5)
    glow(ctx, W / 2, 1450, 560, 0.30)
    for i, (x, ph, d) in enumerate([(250, 0.3, 0.4), (540, 2.1, 1.0), (830, 4.0, 1.5)]):
        lg = ease((t - ps(2) - d * 0.6) / 0.8) * (0.7 + 0.3 * k3)
        girl(ctx, x, 1780, 2.15, t, ph, laugh=lg)
    desk(ctx, W / 2, 1620, 1040)
    if t > ps(3) - 0.1:
        pulse = 0.5 + 0.5 * math.sin(t * 7)
        vignette(ctx, (0.35 + 0.25 * pulse) * k3, col=(0.5, 0, 0.02))

GRID = sorted([(90 + (i % 7) * 150 + ((i // 7) % 2) * 75, 1330 + (i // 7) * 115, 0.62 + (i // 7) * 0.16, i * 2.37) for i in range(35)], key=lambda p: p[1])

def scene_D(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['cal'], lt, 1.0, 1.05, e - s)
    glow(ctx, W / 2, 1200, 700, 0.18)
    dark_floor(ctx, 1330)
    n = int(len(GRID) * ease(lt / 2.2))
    rng = random.Random(8); order = list(range(len(GRID))); rng.shuffle(order)
    on = set(order[:n])
    for i, (x, y, sc, ph) in enumerate(GRID):
        if x > W + 30: continue
        girl(ctx, x, y, sc, t, ph, laugh=0.9 if i in on else 0.0, col=SIL if i in on else (0.09, 0.075, 0.07))
    k = ease((lt - 0.2) / 2.2); a = ease(lt / 0.3)
    title(ctx, f'{int(95 * k)}', 560, 230, a, font='Anton', col=(0.85, 0.12, 0.15))
    title(ctx, 'OF 159 GIRLS', 660, 58, a)

def scene_E(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['cal'], lt, 1.0, 1.04, e - s)
    glow(ctx, W / 2, 520, 420, 0.2, col=(0.95, 0.88, 0.72))
    clock(ctx, W / 2, 540, 210, t, lt * 9.0)
    dark_floor(ctx, 1380)
    rng = random.Random(2)
    for i, x in enumerate([150, 330, 540, 750, 930]):
        c0 = ps(6) + 0.2 + rng.uniform(0, 1.6)
        col = ease((t - c0) / 0.6) * (1 if i in (1, 3) else 0)
        sway = ease((t - ps(6)) / 0.5)
        girl(ctx, x + 10 * sway * math.sin(t * 2 + i), 1700, 1.25, t, i * 1.3, laugh=0.9 * (1 - col) if i != 2 else 0.5, collapse=col)
    fog(ctx, 1700, 120, 0.12)

def scene_F(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['school'], lt, 1.06, 1.0, e - s)
    lit = 1.0 - ease((lt - 0.6) / max(0.5, e - s - 1.0))
    school(ctx, W / 2, 1310, 1.15, t, swing=0.35 * math.sin(t * 5) * ease(lt / 0.3), lit=lit)
    fog(ctx, 1330, 110, 0.2)
    a = ease(lt / 0.4)
    title(ctx, 'SCHOOL CLOSED', 330, 80, a, col=(0.85, 0.12, 0.15))
    title(ctx, '18 MARCH 1962', 410, 44, a, col=(0.8, 0.75, 0.65))

def scene_G(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['road'], lt, 1.0, 1.08, e - s)
    k9 = ease((t - ps(9)) / 0.6)
    for i in range(6):
        u = min(0.92, 0.04 + i * 0.09 + lt * 0.035)
        x, y = road_pt(u); sc = 1.55 - 1.3 * u
        girl(ctx, x + 30 * (i % 2), y + 10 * (i % 2), sc, t, i * 1.9, walk=1.0 - 0.4 * k9, laugh=0.75 * k9)
    for hx, hs, kk in [(760, 0.55, 0), (880, 0.48, 1), (960, 0.6, 2)]:
        glow(ctx, hx, 1195, 60, 0.25 * (0.8 + 0.2 * math.sin(t * 9 + kk)))
    if k9 > 0:
        vignette(ctx, (0.3 + 0.15 * math.sin(t * 6)) * k9, col=(0.45, 0, 0.02))

TOWNS = [((260, 1280), 'NSHAMBA', ps(10) + 0.4), ((300, 520), '', ps(11) - 0.1), ((180, 860), '', ps(11) + 0.4), ((420, 1500), '', ps(11) + 0.9)]

def school_icon(ctx, x, y, s, col):
    ctx.set_source_rgb(*col); ctx.rectangle(x - 22 * s, y - 18 * s, 44 * s, 18 * s); ctx.fill()
    ctx.move_to(x - 28 * s, y - 16 * s); ctx.line_to(x, y - 38 * s); ctx.line_to(x + 28 * s, y - 16 * s); ctx.fill()

def scene_H(ctx, t, s, e):
    lt = t - s
    z = bg_paint(ctx, BG['map'], lt, 1.0, 1.06, e - s)
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2)
    kx, ky = 560, 820
    for r0 in range(3):
        r = ((lt * 220 + r0 * 260) % 780)
        ctx.set_source_rgba(*RED, 0.55 * (1 - r / 780)); ctx.set_line_width(6); ctx.arc(kx, ky, r, 0, 2 * math.pi); ctx.stroke()
    glow(ctx, kx, ky, 60, 0.8, col=RED); ctx.set_source_rgb(*RED); ctx.arc(kx, ky, 16, 0, 2 * math.pi); ctx.fill()
    ctx.select_font_face('Cinzel', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(40)
    ctx.set_source_rgb(0.93, 0.87, 0.74); ctx.move_to(kx - 300, ky - 40); ctx.show_text('KASHASHA')
    for (x, y), name, t0 in TOWNS:
        k = ease((t - t0) / 0.5)
        if k <= 0: continue
        # red track
        ctx.set_source_rgba(*RED, 0.9); ctx.set_line_width(7)
        ctx.move_to(kx, ky); ctx.line_to(kx + (x - kx) * k, ky + (y - ky) * k); ctx.stroke()
        if k >= 1:
            glow(ctx, x, y, 70, 0.7, col=RED)
            if name:
                rng = random.Random(4)
                for j in range(40):
                    ctx.set_source_rgba(*RED, 0.9); ctx.arc(x + rng.gauss(0, 34), y + rng.gauss(0, 26), 5, 0, 2 * math.pi); ctx.fill()
                ctx.set_source_rgb(0.93, 0.87, 0.74); ctx.set_font_size(40); ctx.move_to(x - 120, y - 60); ctx.show_text(name)
            else:
                school_icon(ctx, x, y + 14, 1.4, RED)
    ctx.restore()
    tn = TOWNS[0][2]
    if t > tn:
        a = ease((t - tn) / 0.3); cnt = int(217 * ease((t - tn) / 1.4))
        title(ctx, f'{cnt}', 1720, 200, a, font='Anton', col=(0.85, 0.12, 0.15))
        title(ctx, 'VILLAGERS', 1800, 52, a)

def scene_I(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['cal'], lt, 1.0, 1.06, e - s)
    lantern(ctx, 760, 1210, t, 3)
    dark_floor(ctx, 1560)
    ctx.set_source_rgb(*SIL); ctx.rectangle(160, 1540, 760, 26); ctx.fill(); ctx.rectangle(190, 1560, 22, 260); ctx.fill(); ctx.rectangle(870, 1560, 22, 260); ctx.fill()
    microscope(ctx, 640, 1540, 1.5)
    tubes(ctx, 820, 1540, 0.95, fill=0.8)
    doctor(ctx, 360, 1840, 1.75, t)
    a1 = ease((t - s) / 0.4); a2 = ease((t - ps(12) - 1.3) / 0.4)
    title(ctx, 'POISON?', 380, 76, a1)
    title(ctx, 'INFECTION?', 480, 76, a2)
    if t > ps(13) - 0.1:
        k = ease((t - ps(13)) / 0.35); k2 = ease((t - ps(13) - 0.3) / 0.35)
        strike(ctx, 'POISON?', 380, 76, k); strike(ctx, 'INFECTION?', 480, 76, k2)
        title(ctx, 'NOTHING', 660, 150, ease((t - ps(13) - 0.5) / 0.4), font='Anton', col=(0.85, 0.12, 0.15))

MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

def cal_page(ctx, x, y, w, h, m, yr, curl=0.0):
    ctx.save()
    ctx.translate(x, y)
    if curl > 0: ctx.translate(0, -h * 0.0); ctx.scale(1, max(0.02, 1 - curl)); ctx.translate(0, 0)
    ctx.set_source_rgb(0.90, 0.84, 0.72); ctx.rectangle(-w / 2, 0, w, h); ctx.fill()
    ctx.set_source_rgb(*RED); ctx.rectangle(-w / 2, 0, w, 70); ctx.fill()
    ctx.select_font_face('Anton'); ctx.set_font_size(170); ex = ctx.text_extents(m)
    ctx.set_source_rgb(*SIL); ctx.move_to(-ex.x_advance / 2, 290); ctx.show_text(m)
    ctx.select_font_face('Cinzel', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(64); ex = ctx.text_extents(yr)
    ctx.move_to(-ex.x_advance / 2, 400); ctx.show_text(yr)
    ctx.restore()

def scene_J(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['cal'], lt, 1.0, 1.05, e - s)
    glow(ctx, W / 2, 700, 600, 0.2, col=(0.95, 0.88, 0.72))
    x, y, w, h = W / 2, 420, 480, 470
    ctx.set_source_rgb(*SIL); ctx.rectangle(x - w / 2 - 14, y - 30, w + 28, h + 50); ctx.fill()
    ctx.set_source_rgb(0.3, 0.27, 0.24)
    for k in range(6): ctx.arc(x - 150 + k * 60, y - 14, 9, 0, 2 * math.pi); ctx.fill()
    dur = e - s - 0.8; per = dur / 18
    i = min(17, int(lt / per)); f = (lt / per) - int(lt / per) if i < 17 else 0
    m0 = i; m1 = min(17, i + 1)
    cal_page(ctx, x, y, w, h, MONTHS[m1 % 12], '1962' if m1 < 12 else '1963')
    if i < 17:
        c = ease(f * 1.6)
        ctx.push_group(); cal_page(ctx, x, y - 260 * c, w, h, MONTHS[m0 % 12], '1962' if m0 < 12 else '1963'); ctx.pop_group_to_source(); ctx.paint_with_alpha(1 - c)
    a = ease((lt - 0.3) / 0.5)
    title(ctx, '18 MONTHS?', 1380, 120, a, font='Anton', col=(0.85, 0.12, 0.15))
    title(ctx, 'by some accounts', 1460, 44, a, col=(0.8, 0.75, 0.65))

def scene_K(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, BG['cal'], lt, 1.0, 1.05, e - s)
    glow(ctx, W / 2, 1450, 700, 0.22)
    fog(ctx, 1700, 200, 0.12)
    heads = [(200, 1470), (540, 1470), (880, 1470)]
    for i, (hx, hy) in enumerate(heads):
        profile_head(ctx, hx, hy, 0.95)
        if i < 2:
            # red waves travelling from this head's mouth toward the next head
            for j in range(3):
                ph = ((lt * 0.9 + j / 3 - i * 0.33) % 1.0)
                cx = hx + 110 + ph * 150
                ctx.set_source_rgba(*RED, 0.9 * math.sin(ph * math.pi)); ctx.set_line_width(7)
                ctx.arc(cx, hy + 20, 28 + 18 * ph, -0.7, 0.7); ctx.stroke()
        # red glow inside head as it 'catches' it
        k = ease((lt - i * 0.9) / 0.6)
        glow(ctx, hx + 10, hy - 50, 90, 0.5 * k, col=RED)
    a = ease(lt / 0.5)
    title(ctx, 'MASS PSYCHOGENIC', 520, 62, a)
    title(ctx, 'ILLNESS', 600, 62, a)
    title(ctx, 'stress, spreading person to person', 680, 38, a, col=(0.8, 0.75, 0.65))

def scene_L(ctx, t, s, e):
    lt = t - s
    u = ease(lt / (e - s))
    bg_paint(ctx, BG['school'], lt, 1.0, 1.0, e - s)
    z = 1.0 + 0.22 * u
    ctx.save(); ctx.translate(W / 2 + 160, 900); ctx.scale(z, z); ctx.translate(-W / 2 - 160, -900)
    school(ctx, W / 2, 1310, 1.15, t, swing=0.18 * math.sin(t * 2.2), lit=0.25)
    ctx.restore()
    fog(ctx, 1340, 120, 0.22)
    lg = 0.6 * ease((t - ps(17) - 0.8) / 1.2)
    glow(ctx, 250, 1560, 330, 0.28, col=(0.95, 0.88, 0.72))
    girl(ctx, 250, 1820, 2.1, t, 0.7, laugh=lg)
    fog(ctx, 1800, 120, 0.12)

DRAW = {k: globals()['scene_' + k] for k in 'ABCDEFGHIJKL'}

def frame(ctx, name, t, s, e):
    ctx.save(); DRAW[name](ctx, t, s, e); ctx.restore()
    vignette(ctx, 0.8)
    fl = 0.04 * (math.sin(t * 17) * math.sin(t * 5.3) + 1)
    ctx.set_source_rgba(0, 0, 0, fl); ctx.paint()
    k = t - s
    if k < 0.15 and name != 'A': ctx.set_source_rgba(0, 0, 0, 1 - k / 0.15); ctx.paint()
    if name == 'A' and k < 0.4: ctx.set_source_rgba(0, 0, 0, 1 - k / 0.4); ctx.paint()
    if t > TOTAL - 0.6: ctx.set_source_rgba(0, 0, 0, (t - TOTAL + 0.6) / 0.6); ctx.paint()
    draw_captions(ctx, t)

def load_bgs():
    BG.update(sav=savanna_bg(), school=school_bg(), room=room_bg(), road=road_bg(), map=map_bg(), cal=calendar_bg())

def render_scene(idx, out_dir=None):
    out_dir = out_dir or EP + '/out'
    load_bgs()
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
    load_bgs()
    for name, s, e in scene_bounds():
        if s <= t < e: break
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
    ctx.set_source_rgb(0, 0, 0); ctx.paint(); frame(ctx, name, t, s, e); surf.write_to_png(path)

if __name__ == '__main__':
    if sys.argv[1] == 'still':
        for t in sys.argv[2:]: still(float(t), f'{EP}/stills/f_{float(t):05.1f}.png')
    else:
        sys.exit(render_scene(int(sys.argv[1])))
