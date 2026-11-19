import cairo, math, json, random, subprocess, sys, os
W, H, FPS = 1080, 1920, 30
EP = os.environ['EP']
TIM = json.load(open(EP + '/timing.json'))
RED = (0.80, 0.07, 0.12)
SIL = (0.02, 0.02, 0.03)

def ps(i): return TIM[i]['start']

# ---------------- scenes (phrase index ranges) ----------------
SCENES = [('A', 0), ('B', 1), ('C', 4), ('D', 6), ('E', 8), ('F', 10), ('G', 11), ('H', 12), ('I', 13), ('J', 14)]
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

# ---------------- day 4: Great Molasses Flood ----------------
MOL_D = (0.13, 0.035, 0.025)      # molasses deep
MOL_M = (0.36, 0.07, 0.05)        # molasses mid
GROUND_Y = 1560

def word_t(word, after=0.0):
    for g in GROUPS:
        for w in g:
            if w['w'].strip('.,?') == word and w['t0'] >= after: return w['t0']
    return after

def lantern(ctx, x, y, t, k):
    fl = 0.85 + 0.15 * math.sin(t * 13 + k * 2.1) * math.sin(t * 7.3 + k)
    g = cairo.RadialGradient(x, y, 3, x, y, 160)
    g.add_color_stop_rgba(0, 1, 0.7, 0.3, 0.5 * fl); g.add_color_stop_rgba(1, 1, 0.6, 0.25, 0)
    ctx.set_source(g); ctx.arc(x, y, 160, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(1, 0.78, 0.4); ctx.arc(x, y, 9, 0, 2 * math.pi); ctx.fill()

def person(ctx, x, y, s, t, walk=0.0, ph=0.0, col=SIL, lamp=False, cap=True):
    """Feet at (x,y), height ~200*s. walk = stride amount 0..1."""
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.set_source_rgb(*col)
    a = t * 4.0 + ph; st = math.sin(a) * walk
    hip = (0, -95 - abs(st) * 4)
    for side in (-1, 1):
        sw = st * side
        limb(ctx, [hip, (hip[0] + sw * 20, hip[1] + 48), (sw * 32, 0)], 14)
    # coat
    ctx.move_to(-22, -170); ctx.line_to(22, -170); ctx.line_to(30, -78); ctx.line_to(-30, -78); ctx.close_path(); ctx.fill()
    for side in (-1, 1):
        sw = -st * side
        limb(ctx, [(side * 18, -162), (side * 24 + sw * 14, -120), (side * 22 + sw * 20, -86)], 11)
    ctx.arc(0, -188, 17, 0, 2 * math.pi); ctx.fill()
    if cap:
        ctx.move_to(-20, -196); ctx.curve_to(-18, -216, 18, -216, 20, -196); ctx.line_to(30, -194); ctx.line_to(-20, -192); ctx.fill()
    ctx.restore()
    if lamp: lantern(ctx, x + 26 * s, y - 86 * s, t, ph)

def rail_el(ctx, y, x0, x1, col, bend=0.0, bx=W / 2, t=0):
    """Elevated railway girder from x0..x1 at deck height y; bend sags it around bx."""
    def dy(x): return bend * 260 * max(0, 1 - abs(x - bx) / 420) ** 1.5
    ctx.set_source_rgb(*col)
    # deck: top and bottom chords
    for off, wdt in ((0, 14), (46, 10)):
        ctx.set_line_width(wdt); ctx.move_to(x0, y + off + dy(x0))
        for x in range(int(x0), int(x1) + 1, 20): ctx.line_to(x, y + off + dy(x))
        ctx.stroke()
    # lattice
    ctx.set_line_width(5)
    x = x0
    while x < x1:
        ctx.move_to(x, y + dy(x)); ctx.line_to(x + 30, y + 46 + dy(x + 30)); ctx.line_to(x + 60, y + dy(x + 60)); ctx.stroke(); x += 60
    # columns
    for cx in range(int(x0) + 90, int(x1), 260):
        lean = bend * (cx - bx) / 420 * 0.35 * (1 if abs(cx - bx) < 500 else 0)
        ctx.set_line_width(16); ctx.move_to(cx, y + 46 + dy(cx)); ctx.line_to(cx + math.sin(lean) * 400, GROUND_Y + 10); ctx.stroke()
        ctx.set_line_width(5); ctx.move_to(cx - 30, y + 60 + dy(cx)); ctx.line_to(cx + 30, y + 60 + dy(cx)); ctx.stroke()

def tank(ctx, cx, base, w, h, t=0, streaks=0.0, paint=0.0, shake=0.0, crack=0.0):
    """Cylindrical riveted tank, base centre (cx, base). streaks: red leak streaks; paint: brown cover-up 0..1."""
    jx = shake * 6 * math.sin(t * 61); jy = shake * 4 * math.sin(t * 47 + 1)
    ctx.save(); ctx.translate(cx + jx, base + jy)
    ell = w * 0.07
    g = cairo.LinearGradient(-w / 2, 0, w / 2, 0)
    g.add_color_stop_rgb(0, 0.04, 0.04, 0.05); g.add_color_stop_rgb(0.35, 0.16, 0.15, 0.15)
    g.add_color_stop_rgb(0.55, 0.11, 0.10, 0.11); g.add_color_stop_rgb(1, 0.03, 0.03, 0.04)
    ctx.move_to(-w / 2, -h); ctx.line_to(-w / 2, 0)
    ctx.save(); ctx.scale(w / 2, ell); ctx.arc_negative(0, 0, 1, math.pi, 0); ctx.restore()
    ctx.line_to(w / 2, -h); ctx.close_path(); ctx.set_source(g); ctx.fill()
    # roof cone
    ctx.set_source_rgb(0.07, 0.065, 0.07)
    ctx.save(); ctx.scale(w / 2, ell); ctx.arc(0, -h / ell, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    ctx.move_to(-w / 2, -h); ctx.line_to(0, -h - w * 0.09); ctx.line_to(w / 2, -h); ctx.fill()
    # bands + rivets
    nb = 6
    for i in range(1, nb):
        yy = -h * i / nb
        ctx.set_source_rgba(0, 0, 0, 0.55); ctx.set_line_width(max(2, w * 0.004))
        ctx.save(); ctx.scale(1, 1); ctx.move_to(-w / 2, yy)
        ctx.curve_to(-w / 4, yy + ell * 0.9, w / 4, yy + ell * 0.9, w / 2, yy); ctx.restore(); ctx.stroke()
        for k in range(-14, 15):
            u = k / 15; rx = u * w / 2; ry = yy + ell * (1 - u * u) ** 0.5 * 0.75 - 6
            ctx.set_source_rgba(0.35, 0.33, 0.32, 0.35 * (1 - abs(u))); ctx.arc(rx, ry, max(1.5, w * 0.003), 0, 2 * math.pi); ctx.fill()
    for k in range(-5, 6):
        u = k / 6; sx = math.sin(u * math.pi / 2) * w / 2
        ctx.set_source_rgba(0, 0, 0, 0.35); ctx.set_line_width(max(1.5, w * 0.003))
        ctx.move_to(sx, -h); ctx.line_to(sx, ell * (1 - (sx / (w / 2)) ** 2) ** 0.5 * 0.9); ctx.stroke()
    # leak streaks
    if streaks > 0:
        rng = random.Random(11)
        for i in range(16):
            u = rng.uniform(-0.85, 0.85); sx = math.sin(u * math.pi / 2) * w / 2
            y0 = -h * rng.uniform(0.25, 0.9); L = (-y0) * rng.uniform(0.4, 1.0) * min(1, streaks * rng.uniform(0.8, 1.6))
            wd = w * rng.uniform(0.006, 0.014) * (1 - abs(u) * 0.6)
            gg = cairo.LinearGradient(0, y0, 0, y0 + L)
            gg.add_color_stop_rgba(0, *RED, 0.85); gg.add_color_stop_rgba(1, *MOL_M, 0.9)
            ctx.set_source(gg); ctx.move_to(sx - wd / 2, y0); ctx.line_to(sx + wd / 2, y0); ctx.line_to(sx + wd * 0.4, y0 + L)
            ctx.arc(sx, y0 + L, wd * 0.6, 0, math.pi); ctx.line_to(sx - wd * 0.4, y0 + L); ctx.fill()
    # brown paint rolling over from the left
    if paint > 0:
        px = -w / 2 + w * paint
        ctx.save(); ctx.rectangle(-w / 2, -h - w * 0.1, px + w / 2, h + w * 0.2); ctx.clip()
        ctx.move_to(-w / 2, -h); ctx.line_to(-w / 2, 0)
        ctx.save(); ctx.scale(w / 2, ell); ctx.arc_negative(0, 0, 1, math.pi, 0); ctx.restore()
        ctx.line_to(w / 2, -h); ctx.close_path(); ctx.set_source_rgba(0.20, 0.12, 0.08, 0.92); ctx.fill()
        ctx.restore()
    # crack: glowing red split from base upward, molasses bursting
    if crack > 0:
        ch = h * min(1, crack * 1.3)
        rng = random.Random(3); pts = [(w * 0.05, ell * 0.6)]
        y = ell * 0.6
        while y > -ch:
            y -= h * 0.06; pts.append((w * 0.05 + rng.uniform(-1, 1) * w * 0.03 * (1 + crack * 2), y))
        op = w * 0.06 * crack
        ctx.set_source_rgb(*MOL_D)
        ctx.move_to(*pts[0])
        for x, y in pts: ctx.line_to(x - op * (1 + y / h), y)
        for x, y in reversed(pts): ctx.line_to(x + op * (1 + y / h), y)
        ctx.close_path(); ctx.fill_preserve(); ctx.set_source_rgb(*RED); ctx.set_line_width(max(3, w * 0.006)); ctx.stroke()
    ctx.restore()

def rivets_fly(ctx, cx, base, w, h, t, t0):
    if t < t0: return
    rng = random.Random(7)
    for i in range(26):
        st = t0 + rng.uniform(0, 2.4)
        if t < st: continue
        k = t - st
        if k > 1.2: continue
        yy = base - h * rng.uniform(0.15, 0.85); xx = cx + rng.choice((-1, 1)) * w / 2 * rng.uniform(0.6, 0.98)
        vx = (1 if xx > cx else -1) * rng.uniform(300, 700); vy = rng.uniform(-500, -150)
        px = xx + vx * k; py = yy + vy * k + 900 * k * k
        if k < 0.12:
            g = cairo.RadialGradient(xx, yy, 1, xx, yy, 70)
            g.add_color_stop_rgba(0, 1, 0.8, 0.5, 0.9 * (1 - k / 0.12)); g.add_color_stop_rgba(1, 1, 0.6, 0.3, 0)
            ctx.set_source(g); ctx.arc(xx, yy, 70, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgb(0.9, 0.75, 0.55); ctx.arc(px, py, 6, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(0.9, 0.6, 0.3, 0.5); ctx.set_line_width(3); ctx.move_to(px, py); ctx.line_to(px - vx * 0.04, py - (vy + 1800 * k) * 0.04); ctx.stroke()

def molasses_surface(ctx, y, t, x0=-50, x1=W + 50, amp=6, alpha=1.0):
    g = cairo.LinearGradient(0, y - 20, 0, H)
    g.add_color_stop_rgba(0, *MOL_M, alpha); g.add_color_stop_rgba(0.25, *MOL_D, alpha); g.add_color_stop_rgba(1, 0.05, 0.015, 0.01, alpha)
    ctx.move_to(x0, H)
    for x in range(int(x0), int(x1) + 1, 20): ctx.line_to(x, y + amp * math.sin(x / 90 + t * 0.6))
    ctx.line_to(x1, H); ctx.close_path(); ctx.set_source(g); ctx.fill()
    # sheen
    for i in range(7):
        yy = y + 30 + i * i * 9
        if yy > H: break
        ctx.set_source_rgba(0.95, 0.35, 0.25, 0.10 - i * 0.012); ctx.set_line_width(3 + i)
        ctx.move_to(x0, yy)
        for x in range(int(x0), int(x1) + 1, 30): ctx.line_to(x, yy + 4 * math.sin(x / 70 + t * 0.4 + i))
        ctx.stroke()

def wave(ctx, front, base, height, t):
    """Side-on wave moving right; front = x of crest tip."""
    top = base - height
    g = cairo.LinearGradient(0, top, 0, base)
    g.add_color_stop_rgb(0, *MOL_M); g.add_color_stop_rgb(0.4, *MOL_D); g.add_color_stop_rgb(1, 0.05, 0.015, 0.01)
    ctx.move_to(-200, base + 400); ctx.line_to(-200, top + 60)
    for x in range(-200, int(front - height * 0.55), 30):
        ctx.line_to(x, top + 40 + 25 * math.sin(x / 80 + t * 3) + 15 * math.sin(x / 33 - t * 5))
    # curling crest
    cx = front - height * 0.3
    ctx.curve_to(cx, top - 30, front + 40, top + height * 0.05, front, top + height * 0.35)
    ctx.curve_to(front - 40, top + height * 0.25, front - height * 0.18, top + height * 0.3, front - height * 0.12, top + height * 0.5)
    ctx.curve_to(front - 20, top + height * 0.7, front + height * 0.25, base - 40, front + height * 0.4, base)
    ctx.line_to(front + height * 0.4, base + 400); ctx.close_path()
    ctx.set_source(g); ctx.fill()
    # red highlight on crest
    ctx.set_source_rgba(*RED, 0.9); ctx.set_line_width(10)
    ctx.move_to(cx - 200, top + 40); ctx.curve_to(cx, top - 30, front + 40, top + height * 0.05, front, top + height * 0.35); ctx.stroke()
    ctx.set_source_rgba(1, 0.5, 0.4, 0.35); ctx.set_line_width(4)
    ctx.move_to(cx - 120, top + 46); ctx.curve_to(cx, top - 10, front + 10, top + height * 0.08, front - 6, top + height * 0.3); ctx.stroke()
    # drips off the crest
    rng = random.Random(2)
    for i in range(10):
        k = (t * 1.3 + rng.random()) % 1.0
        dx = front - rng.uniform(0, 60); dy = top + height * 0.35 + k * height * 0.5
        ctx.set_source_rgba(*MOL_M, 1 - k); ctx.arc(dx, dy, 8 * (1 - k * 0.5), 0, 2 * math.pi); ctx.fill()

def snow(ctx, t, n=90, seed=1, a=0.55):
    rng = random.Random(seed)
    for i in range(n):
        x0 = rng.uniform(0, W); sp = rng.uniform(60, 140); r = rng.uniform(2, 5); ph = rng.uniform(0, 100)
        y = (ph * 19 + t * sp) % (H + 40) - 20; x = x0 + 30 * math.sin(t * 0.8 + ph)
        ctx.set_source_rgba(0.95, 0.92, 0.88, a * rng.uniform(0.4, 1)); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

def wisps(ctx, x, y, t, n=7, a=0.5):
    for i in range(n):
        k = ((t * 0.18 + i / n) % 1.0)
        yy = y - k * 700; xx = x + (i - n / 2) * 50
        ctx.set_source_rgba(0.95, 0.55, 0.30, a * math.sin(k * math.pi) * 0.6); ctx.set_line_width(6 + 10 * k)
        ctx.move_to(xx, yy)
        for j in range(1, 8):
            ctx.line_to(xx + 40 * math.sin(j * 0.9 + t * 1.2 + i), yy - j * 22)
        ctx.stroke()

# ---------------- cached backgrounds ----------------
def harbour_bg(night=False):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(100, 100)
    if night: sky(ctx, top=(0.03, 0.035, 0.06), bot=(0.20, 0.16, 0.15), horizon=GROUND_Y - 150); moon(ctx, 820, 330, 60)
    else: sky(ctx, top=(0.09, 0.09, 0.11), bot=(0.42, 0.33, 0.26), horizon=GROUND_Y - 150); moon(ctx, 260, 360, 85)
    # harbour water strip and far shore
    ctx.set_source_rgb(0.12, 0.11, 0.12); ctx.move_to(-100, GROUND_Y - 300)
    for x in range(-100, W + 120, 60): ctx.line_to(x, GROUND_Y - 300 - 30 * math.sin(x / 140) - 15 * math.sin(x / 47))
    ctx.line_to(W + 100, GROUND_Y - 230); ctx.line_to(-100, GROUND_Y - 230); ctx.fill()
    # ships' masts
    ctx.set_source_rgb(0.10, 0.09, 0.10)
    for mx in (140, 190, 950): ctx.rectangle(mx, GROUND_Y - 470, 6, 200); ctx.fill(); ctx.rectangle(mx - 30, GROUND_Y - 430, 66, 4); ctx.fill()
    houses(ctx, GROUND_Y - 120, random.Random(21), (0.08, 0.07, 0.08), 180, 300, lit=0.10, seed_w=(90, 150))
    ground(ctx, GROUND_Y - 10)
    fog(ctx, GROUND_Y - 160, 120, 0.20)
    return surf

def court_bg():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(100, 100)
    ctx.set_source_rgb(0.05, 0.04, 0.04); ctx.paint()
    # tall arched window with moonlight
    wx, wy, ww, wh = W / 2 - 200, 320, 400, 640
    g = cairo.LinearGradient(0, wy, 0, wy + wh)
    g.add_color_stop_rgb(0, 0.30, 0.27, 0.24); g.add_color_stop_rgb(1, 0.55, 0.45, 0.34)
    ctx.move_to(wx, wy + wh); ctx.line_to(wx, wy + ww / 2); ctx.arc(wx + ww / 2, wy + ww / 2, ww / 2, math.pi, 0); ctx.line_to(wx + ww, wy + wh); ctx.close_path()
    ctx.set_source(g); ctx.fill()
    ctx.set_source_rgb(0.05, 0.04, 0.04)
    for k in range(1, 4): ctx.rectangle(wx + ww * k / 4 - 5, wy, 10, wh); ctx.fill()
    for k in range(1, 5): ctx.rectangle(wx, wy + ww / 2 + k * 110, ww, 8); ctx.fill()
    # light shaft
    g = cairo.LinearGradient(0, wy + wh, 0, H)
    g.add_color_stop_rgba(0, 0.9, 0.8, 0.6, 0.18); g.add_color_stop_rgba(1, 0.9, 0.8, 0.6, 0)
    ctx.move_to(wx, wy + wh); ctx.line_to(wx + ww, wy + wh); ctx.line_to(wx + ww + 250, H); ctx.line_to(wx - 250, H); ctx.close_path(); ctx.set_source(g); ctx.fill()
    # judge's bench
    ctx.set_source_rgb(0.025, 0.02, 0.02)
    ctx.rectangle(60, 1330, W - 120, 470); ctx.fill()
    ctx.rectangle(30, 1300, W - 60, 40); ctx.fill()
    ctx.set_source_rgba(0.6, 0.45, 0.3, 0.12)
    for px in range(120, W - 100, 210): ctx.rectangle(px, 1390, 150, 330); ctx.fill()
    return surf

HARB = NIGHT = COURT = None

def bg_paint(ctx, surf, t, z0, z1, dur, dx=0, dy=0):
    z = z0 + (z1 - z0) * ease(t / dur) if dur > 0 else z0
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2 + dx, -H / 2 + dy)
    ctx.set_source_surface(surf, -100, -100); ctx.paint(); ctx.restore()
    return z

# ---------------- scenes ----------------
def scene_A(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, HARB, lt, 1.0, 1.08, e - s)
    tank(ctx, 700, GROUND_Y, 560, 300, t)
    rail_el(ctx, GROUND_Y - 190, -40, W + 40, (0.03, 0.03, 0.035))
    for i, (x, ph) in enumerate([(160, 0), (330, 2), (920, 4)]):
        person(ctx, x + 30 * lt * (1 if i != 1 else -1), GROUND_Y + 160 + i * 40, 1.1 + i * 0.12, t, walk=0.6, ph=ph)
    fog(ctx, GROUND_Y + 60, 120, 0.12)
    a = ease(lt / 0.6) * (1 - ease((lt - (e - s - 0.5)) / 0.4))
    title(ctx, 'BOSTON', 520, 100, a)
    title(ctx, '1919', 660, 130, a, col=RED)

def scene_B(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, HARB, lt, 1.25, 1.35, e - s, dy=-160)
    z = 1.0 + 0.08 * ease(lt / (e - s))
    ctx.save(); ctx.translate(W / 2, 1800); ctx.scale(z, z); ctx.translate(-W / 2, -1800)
    tank(ctx, W / 2, 1900, 1350, 660, t)
    ctx.restore()
    fog(ctx, 1800, 160, 0.18)
    if t > ps(2) - 0.1:
        a = ease((t - ps(2) + 0.1) / 0.4)
        title(ctx, '50 FT TALL', 470, 110, a, font='Anton')
    if t > word_t('MILLION') - 0.2:
        a = ease((t - word_t('MILLION') + 0.2) / 0.4)
        title(ctx, '2,300,000', 650, 150, a, font='Anton', col=RED)
        title(ctx, 'GALLONS OF MOLASSES', 740, 54, a)

def scene_C(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, HARB, lt, 1.3, 1.36, e - s, dy=-160)
    leak = ease(lt / 2.2)
    pt = word_t('PAINTED')
    paint = ease((t - pt) / 2.6) if t > pt else 0
    tank(ctx, W / 2, 1900, 1350, 660, t, streaks=leak, paint=paint)
    # painter on a ladder, moving with the paint edge
    if t > pt - 0.6:
        px = -675 + 1350 * paint + W / 2
        px = max(140, min(W - 140, px))
        ctx.set_source_rgb(*SIL); ctx.set_line_width(9)
        for dx in (-30, 30): ctx.move_to(px + dx - 40, 1820); ctx.line_to(px + dx, 1300); ctx.stroke()
        for ry in range(1340, 1800, 60): ctx.move_to(px - 70 + (1820 - ry) * 0.077, ry); ctx.line_to(px - 10 + (1820 - ry) * 0.077, ry); ctx.stroke()
        person(ctx, px - 20, 1560, 1.25, t, walk=0.15)
        bx = px + 30 + 20 * math.sin(t * 8)
        limb(ctx, [(px - 8, 1360), (bx, 1300)], 10)
        ctx.set_source_rgb(0.25, 0.14, 0.09); ctx.rectangle(bx - 6, 1270, 16, 34); ctx.fill()
    if t < pt:
        title(ctx, 'LEAKING', 560, 120, ease(lt / 0.4), font='Anton', col=RED)
    else:
        title(ctx, 'PAINTED BROWN', 560, 96, ease((t - pt) / 0.4), font='Anton')
        title(ctx, 'to hide the streaks', 640, 50, ease((t - pt - 0.6) / 0.5), col=(0.8, 0.75, 0.65))

def scene_D(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, HARB, lt, 1.3, 1.42, e - s, dy=-160)
    t_open = ps(7)
    sh = 0.3 + 0.7 * ease(lt / 2.0)
    cr = ease((t - t_open) / 1.6) if t > t_open else 0
    tank(ctx, W / 2, 1900, 1350, 660, t, streaks=1.0, paint=1.0, shake=sh, crack=cr)
    rivets_fly(ctx, W / 2, 1900, 1350, 660, t, s + 0.2)
    if cr > 0:
        # burst spreading at base
        g = cairo.RadialGradient(W / 2 + 60, 1820, 20, W / 2 + 60, 1820, 900 * cr)
        g.add_color_stop_rgba(0, *MOL_M, 1); g.add_color_stop_rgba(0.7, *MOL_D, 1); g.add_color_stop_rgba(1, *MOL_D, 0)
        ctx.set_source(g); ctx.save(); ctx.translate(W / 2 + 60, 1840); ctx.scale(1, 0.35); ctx.arc(0, 0, 900 * cr, math.pi, 2 * math.pi); ctx.restore(); ctx.fill()
        ctx.set_source_rgba(1, 0.9, 0.8, 0.5 * max(0, 1 - (t - t_open) / 0.25)); ctx.paint()
    if t < t_open:
        title(ctx, 'BANG. BANG. BANG.', 560, 90, ease((t - word_t('RIVETS')) / 0.3) if t > word_t('RIVETS') else 0, font='Anton')

def scene_E(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, HARB, lt, 1.0, 1.06, e - s)
    rail_el(ctx, GROUND_Y - 190, -40, W + 40, (0.03, 0.03, 0.035))
    u = lt / (e - s)
    front = 60 + (W + 200) * ease(u * 0.95)
    # people fleeing ahead of the wave
    for i, (ox, ph) in enumerate([(380, 0.5), (560, 2.2), (700, 4.1)]):
        px = front + ox * 0.6 + 260 * lt
        if px < W + 120: person(ctx, px, GROUND_Y + 150 + i * 50, 1.1 + 0.1 * i, t * 2.2, walk=1.0, ph=ph)
    wave(ctx, front, GROUND_Y + 360, 950, t)
    if t > word_t('FORTY') - 0.2:
        a = ease((t - word_t('FORTY') + 0.2) / 0.3)
        title(ctx, '40 FT', 470, 170, a, font='Anton', col=RED)
    if t > word_t('THIRTY-FIVE') - 0.2:
        a = ease((t - word_t('THIRTY-FIVE') + 0.2) / 0.3)
        title(ctx, '35 MPH', 640, 120, a, font='Anton')

def scene_F(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, HARB, lt, 1.05, 1.14, e - s, dy=-30)
    bend = ease((t - word_t('BENDS')) / 0.9) if t > word_t('BENDS') else 0
    # crushed houses: tilted dark blocks
    rng = random.Random(8)
    for i in range(6):
        x = 60 + i * 180 + rng.uniform(-20, 20); ang = rng.uniform(-0.35, 0.35) * ease(lt / 0.8)
        ctx.save(); ctx.translate(x, GROUND_Y + 40); ctx.rotate(ang); ctx.set_source_rgb(0.035, 0.03, 0.035)
        hh = rng.uniform(160, 300)
        ctx.rectangle(-70, -hh, 140, hh); ctx.fill()
        ctx.move_to(-78, -hh); ctx.line_to(0, -hh - 70); ctx.line_to(78, -hh); ctx.fill(); ctx.restore()
    rail_el(ctx, GROUND_Y - 190, -40, W + 40, (0.03, 0.03, 0.035), bend=bend, bx=W / 2 + 40, t=t)
    molasses_surface(ctx, GROUND_Y + 60, t)
    # floating planks
    for i in range(5):
        x = 120 + i * 210 + 15 * math.sin(t + i); y = GROUND_Y + 140 + (i % 2) * 120
        ctx.save(); ctx.translate(x, y); ctx.rotate(0.3 * math.sin(i * 2.1)); ctx.set_source_rgb(0.06, 0.04, 0.03); ctx.rectangle(-70, -9, 140, 18); ctx.fill(); ctx.restore()
    fog(ctx, GROUND_Y + 20, 120, 0.12)

def scene_G(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.08, 1.0, e - s)
    molasses_surface(ctx, GROUND_Y + 40, t, alpha=0.9)
    # 21 candles in a gentle arc, lighting one by one
    for i in range(21):
        u = i / 20
        x = 110 + u * (W - 220); y = GROUND_Y + 230 + 70 * math.sin(u * math.pi)
        on = ease((lt - 0.05 * i) / 0.3)
        if on <= 0: continue
        fl = 0.85 + 0.15 * math.sin(t * 11 + i * 1.7)
        g = cairo.RadialGradient(x, y - 30, 2, x, y - 30, 70)
        g.add_color_stop_rgba(0, 1, 0.7, 0.3, 0.55 * on * fl); g.add_color_stop_rgba(1, 1, 0.6, 0.25, 0)
        ctx.set_source(g); ctx.arc(x, y - 30, 70, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgb(0.85, 0.80, 0.70); ctx.rectangle(x - 7, y - 26, 14, 30); ctx.fill()
        ctx.set_source_rgba(1, 0.8, 0.45, on); ctx.save(); ctx.translate(x, y - 34); ctx.scale(5, 10 * fl); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    a = ease(lt / 0.5)
    title(ctx, '21', 600, 260, a, font='Anton', col=RED)
    title(ctx, 'LIVES LOST', 700, 60, a)

def scene_H(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, HARB, lt, 1.15, 1.22, e - s, dy=-60)
    molasses_surface(ctx, GROUND_Y + 80, t * 0.3, amp=3)
    # rescuers wading slowly; lower legs hidden by the syrup
    for i, (x, sc, ph) in enumerate([(230, 1.6, 0.0), (560, 1.9, 1.7), (850, 1.5, 3.1)]):
        y = GROUND_Y + 80 + 70 * sc
        ctx.save(); ctx.rectangle(0, 0, W, GROUND_Y + 82 + 20 * sc); ctx.clip()
        person(ctx, x + 18 * lt * (1 if i % 2 else -1) * 0.5, y, sc, t * 0.35, walk=0.4, ph=ph, lamp=(i != 1))
        ctx.restore()
        # ripple ring
        ctx.set_source_rgba(0.95, 0.35, 0.25, 0.25); ctx.set_line_width(4)
        ctx.save(); ctx.translate(x + 18 * lt * (1 if i % 2 else -1) * 0.5, GROUND_Y + 90 + 20 * sc); ctx.scale(70 * sc, 12 * sc); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.stroke()
        # breath in the cold
        k = (t * 0.7 + i * 0.33) % 1.0
        bx = x + 40 * sc + k * 60; by = y - 190 * sc - 20 - k * 50
        ctx.set_source_rgba(0.9, 0.88, 0.85, 0.25 * (1 - k)); ctx.arc(bx, by, 12 + 30 * k, 0, 2 * math.pi); ctx.fill()
    snow(ctx, t)
    title(ctx, 'THICK AS GLUE', 560, 96, ease(lt / 0.5), font='Anton')

def scene_I(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, COURT, lt, 1.0, 1.07, e - s)
    tc = word_t('COURT')
    # gavel
    hit = t - (tc + 0.7)
    ang = -0.9 if hit < -0.5 else (-0.9 + 0.9 * ease((hit + 0.5) / 0.5) if hit < 0 else 0)
    ctx.save(); ctx.translate(W / 2 + 160, 1290); ctx.rotate(ang); ctx.set_source_rgb(*SIL)
    ctx.rectangle(0, -10, 200, 20); ctx.fill(); ctx.rectangle(-30, -45, 60, 90); ctx.fill(); ctx.restore()
    ctx.set_source_rgb(*SIL); ctx.rectangle(W / 2 + 120, 1290, 80, 14); ctx.fill()
    if 0 <= hit < 0.2: ctx.set_source_rgba(1, 0.9, 0.8, 0.3 * (1 - hit / 0.2)); ctx.paint()
    if t < tc:
        a = ease(lt / 0.4)
        title(ctx, 'SABOTAGE?', 230, 100, a, font='Anton')
    else:
        a = ease((t - tc) / 0.4)
        title(ctx, '1925', 230, 110, a, col=RED)
        title(ctx, 'THE TANK', 1520, 90, ease((hit) / 0.3) if hit > 0 else 0, font='Anton')
        title(ctx, 'WAS UNSOUND', 1620, 90, ease((hit) / 0.3) if hit > 0 else 0, font='Anton', col=RED)

def scene_J(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.0, 1.15, e - s, dy=-60)
    # ruined tank base: jagged ring
    ctx.set_source_rgb(0.03, 0.03, 0.035)
    rng = random.Random(4); cx, base, w = W / 2, GROUND_Y + 40, 640
    ctx.move_to(cx - w / 2, base)
    for k in range(0, 21):
        x = cx - w / 2 + w * k / 20; ctx.line_to(x, base - rng.uniform(20, 140))
    ctx.line_to(cx + w / 2, base); ctx.close_path(); ctx.fill()
    molasses_surface(ctx, GROUND_Y + 70, t * 0.3, amp=3, alpha=0.85)
    wisps(ctx, W / 2, GROUND_Y - 20, t, a=0.55 * ease(lt / 1.0))
    if t > ps(15) - 0.2:
        a = ease((t - ps(15) + 0.2) / 0.8)
        person(ctx, W / 2 + 330, GROUND_Y + 330, 1.5, t, col=(0.02 * a + 0.13 * (1 - a),) * 3)
    fog(ctx, GROUND_Y + 60, 130, 0.15)

DRAW = {'A': scene_A, 'B': scene_B, 'C': scene_C, 'D': scene_D, 'E': scene_E, 'F': scene_F, 'G': scene_G, 'H': scene_H, 'I': scene_I, 'J': scene_J}

def build_bgs():
    global HARB, NIGHT, COURT
    HARB = harbour_bg(); NIGHT = harbour_bg(night=True); COURT = court_bg()

def frame(ctx, name, t, s, e):
    ctx.save(); DRAW[name](ctx, t, s, e); ctx.restore()
    vignette(ctx, 0.8)
    fl = 0.04 * (math.sin(t * 17) * math.sin(t * 5.3) + 1)
    ctx.set_source_rgba(0, 0, 0, fl); ctx.paint()
    k = t - s
    if k < 0.15 and name != 'A': ctx.set_source_rgba(0, 0, 0, 1 - k / 0.15); ctx.paint()
    if name == 'A' and k < 0.4: ctx.set_source_rgba(0, 0, 0, 1 - k / 0.4); ctx.paint()
    draw_captions(ctx, t)

def render_scene(idx, out_dir=None):
    out_dir = out_dir or EP + '/out'
    build_bgs()
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
    build_bgs()
    for name, s, e in scene_bounds():
        if s <= t < e: break
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
    ctx.set_source_rgb(0, 0, 0); ctx.paint(); frame(ctx, name, t, s, e); surf.write_to_png(path)

if __name__ == '__main__':
    if sys.argv[1] == 'still':
        for t in sys.argv[2:]: still(float(t), f'{EP}/stills/f_{float(t):05.1f}.png')
    else:
        sys.exit(render_scene(int(sys.argv[1])))
