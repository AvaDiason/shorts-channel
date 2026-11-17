import cairo, math, json, random, subprocess, sys, os
W, H, FPS = 1080, 1920, 30
EP = os.environ['EP']
TIM = json.load(open(EP + '/timing.json'))
RED = (0.80, 0.07, 0.12)
SIL = (0.02, 0.02, 0.03)

def ps(i): return TIM[i]['start']

# ---------------- scenes (phrase index ranges) ----------------
SCENES = [('A', 0), ('B', 2), ('C', 3), ('D', 5), ('E', 7), ('F', 9), ('G', 11), ('H', 14)]
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

def stars(ctx, seed=2, n=90, ymax=900):
    rng = random.Random(seed)
    for _ in range(n):
        ctx.set_source_rgba(0.95, 0.9, 0.8, rng.uniform(0.15, 0.6))
        ctx.arc(rng.uniform(0, W + 200) - 100, rng.uniform(-100, ymax), rng.uniform(1, 2.6), 0, 2 * math.pi); ctx.fill()

def fog(ctx, y, h, a=0.25):
    g = cairo.LinearGradient(0, y - h, 0, y + h)
    g.add_color_stop_rgba(0, 0.6, 0.55, 0.5, 0); g.add_color_stop_rgba(0.5, 0.6, 0.55, 0.5, a); g.add_color_stop_rgba(1, 0.6, 0.55, 0.5, 0)
    ctx.set_source(g); ctx.rectangle(0, y - h, W, 2 * h); ctx.fill()

def drift_fog(ctx, y, h, a, t, speed=20):
    for k in range(3):
        x = ((t * speed * (1 + 0.4 * k) + k * 420) % (W + 900)) - 450
        g = cairo.RadialGradient(x, y + k * 30, 10, x, y + k * 30, 520)
        g.add_color_stop_rgba(0, 0.62, 0.57, 0.52, a); g.add_color_stop_rgba(1, 0.62, 0.57, 0.52, 0)
        ctx.save(); ctx.translate(0, y + k * 30); ctx.scale(1, h / 520); ctx.translate(0, -(y + k * 30))
        ctx.set_source(g); ctx.arc(x, y + k * 30, 520, 0, 2 * math.pi); ctx.fill(); ctx.restore()

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

def lantern(ctx, x, y, t, k, r=160, a=0.5):
    fl = 0.85 + 0.15 * math.sin(t * 13 + k * 2.1) * math.sin(t * 7.3 + k)
    g = cairo.RadialGradient(x, y, 3, x, y, r)
    g.add_color_stop_rgba(0, 1, 0.7, 0.3, a * fl); g.add_color_stop_rgba(1, 1, 0.6, 0.25, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(1, 0.78, 0.4); ctx.arc(x, y, 9, 0, 2 * math.pi); ctx.fill()

def wave_y(x, t, base, amp, k=0):
    return base + amp * (math.sin(x / 140 + t * 1.1 + k) * 0.6 + math.sin(x / 57 - t * 1.7 + k * 2) * 0.3 + math.sin(x / 23 + t * 2.3) * 0.1)

def sea(ctx, t, horizon, col=(0.06, 0.06, 0.08), rows=9, moon_x=None):
    """Animated layered swells from horizon to bottom."""
    ctx.set_source_rgb(*col); ctx.rectangle(-150, horizon, W + 300, H - horizon + 100); ctx.fill()
    if moon_x is not None:   # moon path glitter
        rng = random.Random(int(t * 6))
        for i in range(70):
            y = horizon + (i / 70) ** 1.5 * (H - horizon)
            w = 20 + (y - horizon) * 0.35
            if rng.random() < 0.6:
                ctx.set_source_rgba(0.95, 0.85, 0.65, 0.35 * (1 - i / 90))
                ctx.rectangle(moon_x - w / 2 + rng.uniform(-w, w) * 0.5, y, w * rng.uniform(0.2, 0.7), 2 + i * 0.12); ctx.fill()
    for r in range(rows):
        u = (r + 1) / rows
        base = horizon + (H - horizon) * u ** 1.6
        amp = 4 + 34 * u
        shade = 0.02 + 0.05 * (1 - u)
        ctx.set_source_rgba(shade, shade, shade * 1.25, 0.9)
        ctx.move_to(-150, H + 100)
        for x in range(-150, W + 160, 18): ctx.line_to(x, wave_y(x * (1.6 - u), t, base, amp, r))
        ctx.line_to(W + 160, H + 100); ctx.close_path(); ctx.fill()
        # crest highlight
        ctx.set_source_rgba(0.85, 0.75, 0.6, 0.06 + 0.06 * (1 - u)); ctx.set_line_width(2)
        ctx.move_to(-10, wave_y(-10 * (1.6 - u), t, base, amp, r))
        for x in range(-10, W + 20, 18): ctx.line_to(x, wave_y(x * (1.6 - u), t, base, amp, r))
        ctx.stroke()

def ship(ctx, x, y, s, t, roll=0.04, col=SIL, sail=(0.13, 0.12, 0.12), torn=True, boat=False, rope=0.0):
    """Two-masted brigantine silhouette. (x,y) = waterline centre, length ~ 700*s."""
    ctx.save(); ctx.translate(x, y); ctx.rotate(math.sin(t * 0.9) * roll); ctx.translate(0, math.sin(t * 1.3) * 6 * s); ctx.scale(s, s)
    # sails (behind rigging)
    ctx.set_source_rgb(*sail)
    fm, mm = 140, -110          # foremast, mainmast x
    for i, (w0, w1, y0, y1) in enumerate([(150, 170, -560, -470), (170, 190, -460, -360), (190, 210, -350, -230)]):
        if torn and i == 1: continue      # one sail missing
        bil = 12 * math.sin(t * 1.6 + i)
        ctx.move_to(fm - w0 / 2, y0); ctx.line_to(fm + w0 / 2, y0)
        ctx.curve_to(fm + w1 / 2 + bil, (y0 + y1) / 2, fm + w1 / 2 + bil, (y0 + y1) / 2, fm + w1 / 2, y1)
        if torn and i == 2:
            for k in range(6, -1, -1): ctx.line_to(fm - w1 / 2 + k * w1 / 6, y1 - (18 if k % 2 else 0))
        else:
            ctx.line_to(fm - w1 / 2, y1)
        ctx.close_path(); ctx.fill()
    # main fore-and-aft sail (half furled)
    ctx.move_to(mm, -520); ctx.line_to(mm, -150); ctx.line_to(mm - 230, -170); ctx.curve_to(mm - 150, -300, mm - 60, -420, mm, -520); ctx.fill()
    # jib
    ctx.move_to(fm + 10, -460); ctx.line_to(370, -120); ctx.line_to(fm + 30, -150); ctx.close_path(); ctx.fill()
    ctx.set_source_rgb(*col)
    # masts and rigging
    limb(ctx, [(fm, -40), (fm, -600)], 10); limb(ctx, [(mm, -40), (mm, -580)], 11)
    for yy, ww in [(-560, 160), (-460, 180), (-350, 200)]: limb(ctx, [(fm - ww / 2, yy), (fm + ww / 2, yy)], 5)
    ctx.set_line_width(2)
    for a, b in [((fm, -600), (420, -70)), ((fm, -600), (mm, -60)), ((mm, -580), (-330, -50)), ((fm, -600), (40, -60)), ((mm, -580), (fm, -60))]:
        ctx.move_to(*a); ctx.line_to(*b); ctx.stroke()
    limb(ctx, [(300, -70), (440, -120)], 7)   # bowsprit
    # hull
    ctx.move_to(-340, -80); ctx.line_to(320, -80); ctx.curve_to(340, -60, 330, -20, 300, 10)
    ctx.line_to(-300, 10); ctx.curve_to(-330, -10, -345, -50, -340, -80); ctx.close_path(); ctx.fill()
    ctx.rectangle(-330, -100, 120, 22); ctx.fill()   # deckhouse aft
    ctx.rectangle(-60, -102, 110, 24); ctx.fill()     # cabin
    if boat:   # lifeboat on deck
        ctx.move_to(-20, -102); ctx.curve_to(0, -130, 120, -130, 150, -102); ctx.fill()
    if rope > 0:   # red rope trailing astern
        ctx.set_source_rgb(*RED); ctx.set_line_width(7)
        ctx.move_to(-335, -70)
        ctx.curve_to(-380, -40, -420 - 40 * rope, 0, -470 - 140 * rope, 20 + 4 * math.sin(t * 2))
        ctx.stroke()
    ctx.restore()

def sailor(ctx, x, y, s, pose=0.0, col=SIL):
    """Seated rower. pose 0..1 = stroke phase."""
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.set_source_rgb(*col)
    lean = -0.35 + 0.7 * pose
    neck = (math.sin(lean) * 70, -math.cos(lean) * 70)
    limb(ctx, [(0, 0), neck], 26)
    ctx.arc(neck[0] + math.sin(lean) * 22, neck[1] - 22, 15, 0, 2 * math.pi); ctx.fill()
    ctx.rectangle(neck[0] + math.sin(lean) * 22 - 16, neck[1] - 42, 32, 10); ctx.fill()   # cap
    hand = (neck[0] + 55 - 40 * pose, neck[1] + 40)
    limb(ctx, [(neck[0], neck[1] + 10), hand], 9)
    limb(ctx, [(0, 0), (40, -18), (60, 12)], 12)
    # oar
    ctx.set_line_width(6); ctx.move_to(hand[0] - 30, hand[1] - 10); ctx.line_to(hand[0] + 160, hand[1] + 90 - 40 * pose); ctx.stroke()
    ctx.restore()

def human(ctx, x, y, s, kind, col=SIL, a=1.0):
    """Standing figure for the 'who was aboard' line. kind: captain, wife, child, crew."""
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.set_source_rgba(*col, a)
    if kind == 'child':
        ctx.move_to(-28, 0); ctx.line_to(-18, -70); ctx.line_to(18, -70); ctx.line_to(28, 0); ctx.fill()
        ctx.arc(0, -88, 18, 0, 2 * math.pi); ctx.fill()
    elif kind == 'wife':
        ctx.move_to(-62, 0); ctx.curve_to(-40, -60, -26, -110, -20, -150); ctx.line_to(20, -150); ctx.curve_to(26, -110, 40, -60, 62, 0); ctx.fill()
        ctx.rectangle(-22, -200, 44, 60); ctx.fill()
        ctx.arc(0, -222, 20, 0, 2 * math.pi); ctx.fill(); ctx.arc(-4, -238, 14, 0, 2 * math.pi); ctx.fill()
        limb(ctx, [(-20, -190), (-36, -140), (-40, -115)], 10)
        limb(ctx, [(20, -190), (44, -150), (66, -130)], 10)   # reaching to child
    else:
        limb(ctx, [(-14, 0), (-12, -100)], 15); limb(ctx, [(14, 0), (12, -100)], 15)
        ctx.move_to(-30, -100); ctx.line_to(30, -100); ctx.line_to(32, -200); ctx.line_to(-32, -200); ctx.fill()
        if kind == 'captain':
            ctx.move_to(-32, -200); ctx.line_to(-38, -80); ctx.line_to(38, -80); ctx.line_to(32, -200); ctx.fill()  # coat
        limb(ctx, [(-30, -190), (-40, -140), (-38, -100)], 11); limb(ctx, [(30, -190), (40, -140), (38, -100)], 11)
        ctx.arc(0, -225, 21, 0, 2 * math.pi); ctx.fill()
        if kind == 'captain':
            ctx.rectangle(-30, -248, 60, 10); ctx.fill(); ctx.rectangle(-20, -270, 40, 24); ctx.fill()
        else:
            ctx.arc(0, -238, 18, math.pi, 0); ctx.fill()
    ctx.restore()

def bg_paint(ctx, surf, t, z0, z1, dur, dx=0, dy=0):
    z = z0 + (z1 - z0) * ease(t / dur) if dur > 0 else z0
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2 + dx, -H / 2 + dy)
    ctx.set_source_surface(surf, -100, -100); ctx.paint(); ctx.restore()
    return z

def push(ctx, lt, dur, z0, z1, cx=W / 2, cy=H / 2):
    z = z0 + (z1 - z0) * ease(lt / dur)
    ctx.translate(cx, cy); ctx.scale(z, z); ctx.translate(-cx, -cy)

# ---------------- cached backgrounds ----------------
def night_bg():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(100, 100)
    sky(ctx, top=(0.03, 0.04, 0.07), bot=(0.30, 0.22, 0.17), horizon=1200); stars(ctx)
    moon(ctx, 780, 300, 66)
    # cloud bands
    for y, a in [(420, 0.12), (520, 0.08), (860, 0.1)]:
        fog(ctx, y, 40, a)
    return surf

def cabin_bg():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(-0, 0)
    ctx.set_source_rgb(0.10, 0.07, 0.05); ctx.paint()
    # wooden planks
    rng = random.Random(7)
    for x in range(0, W + 200, 90):
        sh = rng.uniform(0.08, 0.13)
        ctx.set_source_rgb(sh, sh * 0.72, sh * 0.5); ctx.rectangle(x, 0, 86, H + 200); ctx.fill()
    # ceiling beams
    ctx.set_source_rgb(0.03, 0.02, 0.02)
    for y in (120, 380): ctx.rectangle(0, y, W + 200, 60); ctx.fill()
    # porthole with moonlight
    cx, cy = 900, 520
    ctx.set_source_rgb(0.03, 0.02, 0.02); ctx.arc(cx, cy, 120, 0, 2 * math.pi); ctx.fill()
    g = cairo.LinearGradient(0, cy - 100, 0, cy + 100); g.add_color_stop_rgb(0, 0.10, 0.11, 0.16); g.add_color_stop_rgb(1, 0.35, 0.28, 0.22)
    ctx.set_source(g); ctx.arc(cx, cy, 96, 0, 2 * math.pi); ctx.fill()
    moon(ctx, cx + 30, cy - 30, 22)
    ctx.set_source_rgb(0.03, 0.02, 0.02); ctx.set_line_width(6); ctx.move_to(cx - 96, cy); ctx.line_to(cx + 96, cy); ctx.stroke()
    # floor
    ctx.set_source_rgb(0.05, 0.035, 0.03); ctx.rectangle(0, 1820, W + 200, 400); ctx.fill()
    return surf

def chart_bg():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W + 200, H + 200)
    ctx = cairo.Context(surf); ctx.translate(100, 100)
    ctx.set_source_rgb(0.05, 0.035, 0.03); ctx.paint()
    # parchment
    g = cairo.RadialGradient(W / 2, 760, 50, W / 2, 760, 900)
    g.add_color_stop_rgb(0, 0.62, 0.50, 0.34); g.add_color_stop_rgb(1, 0.30, 0.22, 0.14)
    ctx.set_source(g); ctx.rectangle(60, 160, W - 120, 1260); ctx.fill()
    ctx.set_source_rgba(0.2, 0.13, 0.07, 0.35); ctx.set_line_width(2)
    for i in range(1, 7):   # grid
        ctx.move_to(60 + i * (W - 120) / 7, 160); ctx.line_to(60 + i * (W - 120) / 7, 1420); ctx.stroke()
    for i in range(1, 9):
        ctx.move_to(60, 160 + i * 140); ctx.line_to(W - 60, 160 + i * 140); ctx.stroke()
    # coastline of Portugal (right edge)
    ctx.set_source_rgba(0.22, 0.15, 0.09, 0.85)
    ctx.move_to(W - 60, 300); ctx.curve_to(W - 140, 420, W - 110, 560, W - 170, 700); ctx.curve_to(W - 150, 820, W - 190, 900, W - 140, 960)
    ctx.line_to(W - 60, 960); ctx.close_path(); ctx.fill()
    # Azores islands (left)
    for ix, iy, r in [(210, 520, 18), (250, 560, 12), (300, 540, 22), (330, 600, 9), (390, 640, 16)]:
        ctx.save(); ctx.translate(ix, iy); ctx.scale(r * 1.6, r); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    ctx.select_font_face('Cinzel', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(40)
    ctx.move_to(170, 470); ctx.show_text('AZORES')
    ctx.set_font_size(30); ctx.move_to(W - 330, 1000); ctx.show_text('PORTUGAL')
    ctx.set_font_size(34); ctx.move_to(300, 1300); ctx.show_text('ATLANTIC  OCEAN')
    # compass rose
    cx, cy = 230, 1150
    for k in range(8):
        a = k * math.pi / 4; L = 90 if k % 2 == 0 else 50
        ctx.move_to(cx, cy); ctx.line_to(cx + math.cos(a - 0.12) * 18, cy + math.sin(a - 0.12) * 18)
        ctx.line_to(cx + math.cos(a) * L, cy + math.sin(a) * L); ctx.line_to(cx + math.cos(a + 0.12) * 18, cy + math.sin(a + 0.12) * 18); ctx.close_path(); ctx.fill()
    # stains
    rng = random.Random(3)
    for _ in range(14):
        x, y, r = rng.uniform(80, W - 80), rng.uniform(180, 1400), rng.uniform(30, 120)
        g = cairo.RadialGradient(x, y, 0, x, y, r); g.add_color_stop_rgba(0, 0.15, 0.08, 0.03, 0.18); g.add_color_stop_rgba(1, 0.15, 0.08, 0.03, 0)
        ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
    return surf

NIGHT = CABIN = CHART = None
AZ = (360, 600); FOUND = (700, 760)

# ---------------- scenes ----------------
def scene_A(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.0, 1.06, e - s)
    ctx.save(); push(ctx, lt, e - s, 1.0, 1.10, W / 2, 1500)
    sea(ctx, t, 1380, moon_x=780)
    ship(ctx, 560 - lt * 6, 1560, 0.78, t, roll=0.05)
    ctx.restore()
    drift_fog(ctx, 1560, 90, 0.22, t)
    a = ease(lt / 0.6) * (1 - ease((lt - (e - s - 0.6)) / 0.5))
    title(ctx, 'NORTH ATLANTIC', 520, 78, a)
    title(ctx, '1872', 660, 130, a, col=RED)

def wheel(ctx, x, y, r, ang):
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.set_source_rgb(*SIL)
    ctx.set_line_width(r * 0.14); ctx.arc(0, 0, r, 0, 2 * math.pi); ctx.stroke()
    ctx.set_line_width(r * 0.06); ctx.arc(0, 0, r * 0.55, 0, 2 * math.pi); ctx.stroke()
    ctx.arc(0, 0, r * 0.16, 0, 2 * math.pi); ctx.fill()
    for k in range(8):
        a = k * math.pi / 4
        limb(ctx, [(0, 0), (math.cos(a) * r * 1.38, math.sin(a) * r * 1.38)], r * 0.07)
        ctx.arc(math.cos(a) * r * 1.38, math.sin(a) * r * 1.38, r * 0.07, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def scene_B(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.25, 1.32, e - s, dy=-60)
    ctx.save(); ctx.rotate(math.sin(t * 0.9) * 0.03)
    sea(ctx, t, 1300, rows=5, moon_x=780)
    # deck rail (low) + lit deck planks
    ctx.set_source_rgb(*SIL)
    for x in range(-40, W + 60, 110): ctx.rectangle(x, 1430, 14, 120); ctx.fill()
    ctx.rectangle(-100, 1420, W + 200, 18); ctx.fill()
    g = cairo.LinearGradient(0, 1540, 0, H); g.add_color_stop_rgb(0, 0.16, 0.11, 0.08); g.add_color_stop_rgb(1, 0.04, 0.03, 0.03)
    ctx.set_source(g); ctx.rectangle(-100, 1540, W + 200, 600); ctx.fill()
    ctx.set_source_rgba(0, 0, 0, 0.5); ctx.set_line_width(3)
    for x in range(-300, W + 400, 90): ctx.move_to(W / 2 + (x - W / 2) * 0.35, 1540); ctx.line_to(x, H + 50); ctx.stroke()
    # binnacle stand + wheel
    ctx.set_source_rgb(*SIL); ctx.rectangle(W / 2 - 34, 1420, 68, 260); ctx.fill()
    ctx.save(); ctx.translate(0, 0); ctx.set_source_rgba(0, 0, 0, 0.6); ctx.save(); ctx.translate(W / 2, 1690); ctx.scale(200, 30); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill(); ctx.restore()
    wheel(ctx, W / 2, 1380, 210, 0.4 * math.sin(t * 0.7) + lt * 0.05)
    ctx.restore()
    lantern(ctx, 190, 1250, t, 1, r=200, a=0.35)

def scene_C(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.0, 1.04, e - s)
    ctx.save(); push(ctx, lt, e - s, 1.0, 1.15, W / 2, 1200)
    ship(ctx, 600, 1180, 1.25, t, roll=0.03)
    sea(ctx, t, 1170, moon_x=780)
    # rowboat approaching, low in frame
    bx = 520 + 140 * ease(lt / (e - s)); by = 1680 + 6 * math.sin(t * 1.4)
    g = cairo.RadialGradient(bx, by - 40, 20, bx, by - 40, 480); g.add_color_stop_rgba(0, 0.85, 0.72, 0.5, 0.16); g.add_color_stop_rgba(1, 0.85, 0.72, 0.5, 0)
    ctx.set_source(g); ctx.save(); ctx.translate(bx, by - 40); ctx.scale(1, 0.45); ctx.arc(0, 0, 480, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    ctx.save(); ctx.translate(bx, by); ctx.rotate(math.sin(t * 1.1) * 0.04)
    ctx.set_source_rgb(*SIL)
    ctx.move_to(-260, -40); ctx.line_to(240, -50); ctx.curve_to(230, 10, 160, 40, 90, 40); ctx.line_to(-200, 40); ctx.curve_to(-240, 20, -258, -10, -260, -40); ctx.fill()
    for i, sx in enumerate([-150, -30, 90]):
        sailor(ctx, sx, -40, 1.1, 0.5 + 0.5 * math.sin(t * 2.4 - i * 0.3))
    lantern(ctx, 200, -110, t, 3, r=260, a=0.6)
    limb(ctx, [(200, -40), (200, -100)], 5)
    ctx.restore()
    ctx.restore()
    drift_fog(ctx, 1180, 110, 0.18, t, 30)
    # "Nothing." -> dim + silence beat
    k = ease((t - ps(4)) / 0.4)
    ctx.set_source_rgba(0, 0, 0, 0.35 * k); ctx.paint()

def barrel(ctx, x, y, s):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    ctx.set_source_rgb(*SIL)
    ctx.move_to(-60, 0); ctx.curve_to(-78, -60, -78, -120, -60, -180); ctx.line_to(60, -180); ctx.curve_to(78, -120, 78, -60, 60, 0); ctx.fill()
    ctx.set_source_rgba(0.35, 0.25, 0.15, 0.6); ctx.set_line_width(5)
    for yy in (-30, -150): ctx.move_to(-66, yy); ctx.line_to(66, yy); ctx.stroke()
    ctx.restore()

def scene_D(ctx, t, s, e):
    lt = t - s
    sway = math.sin(t * 0.9) * 0.025
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.rotate(sway); ctx.translate(-W / 2, -H / 2)
    bg_paint(ctx, CABIN, lt, 1.08, 1.16, e - s)
    # hanging lantern swings opposite the roll
    lx = W / 2 - 160 + math.sin(t * 0.9 + 0.6) * 60
    ctx.set_source_rgb(*SIL); ctx.set_line_width(3); ctx.move_to(W / 2 - 160, 180); ctx.line_to(lx, 470); ctx.stroke()
    ctx.rectangle(lx - 22, 470, 44, 60); ctx.fill()
    lantern(ctx, lx, 505, t, 0, r=520, a=0.45)
    # supplies: barrels + sacks left, sea chests + hanging coats right
    for bx, by, bs in [(130, 1800, 1.5), (330, 1820, 1.6), (230, 1560, 1.3), (90, 1550, 1.1)]:
        barrel(ctx, bx, by, bs)
    ctx.set_source_rgb(*SIL)
    if t > ps(6) - 0.1:
        k = ease((t - ps(6) + 0.1) / 0.4)
        ctx.save(); ctx.translate(0, (1 - k) * 60); ctx.set_source_rgba(*SIL, k)
        for cx in (650, 880):  # sea chests
            ctx.rectangle(cx - 110, 1660, 220, 160); ctx.fill()
            ctx.arc(cx, 1660, 110, math.pi, 0); ctx.fill()
        for i, hx in enumerate((620, 760, 900)):   # oilskins on pegs
            sw = math.sin(t * 0.9 + i) * 6
            ctx.move_to(hx, 1180); ctx.line_to(hx - 60 + sw, 1480); ctx.line_to(hx + 60 + sw, 1480); ctx.close_path(); ctx.fill()
            ctx.arc(hx, 1180, 14, 0, 2 * math.pi); ctx.fill()
        # boots
        for bx in (520, 580):
            ctx.rectangle(bx, 1730, 34, 90); ctx.fill(); ctx.rectangle(bx, 1800, 60, 22); ctx.fill()
        ctx.restore()
    ctx.restore()
    if t < ps(6) - 0.1:
        a = ease((t - ps(5)) / 0.4) * (1 - ease((t - ps(6) + 0.5) / 0.4))
        title(ctx, '6', 560, 250, a, font='Anton', col=RED)
        title(ctx, 'MONTHS OF SUPPLIES', 660, 54, a)

def scene_E(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.0, 1.05, e - s)
    sea(ctx, t, 1300, rows=6, moon_x=780)
    ctx.save(); ctx.translate(0, 0); ctx.rotate(math.sin(t * 0.9) * 0.015)
    ctx.set_source_rgb(*SIL); ctx.rectangle(-100, 1500, W + 200, 600); ctx.fill()
    for x in range(-40, W + 60, 120): ctx.rectangle(x, 1360, 14, 150); ctx.fill()
    ctx.rectangle(-100, 1350, W + 200, 20); ctx.fill()
    # empty deck at phrase 7; at phrase 8 the people appear as ghosts one by one, then fade
    figs = [('captain', 260, 1.25, 0.15), ('wife', 470, 1.2, 1.1), ('child', 610, 1.25, 2.3), ('crew', 780, 1.15, 3.5), ('crew', 900, 1.05, 3.7), ('crew', 1000, 0.95, 3.9)]
    for kind, x, sc, d in figs:
        if t < ps(8): continue
        a_in = ease((t - ps(8) - d) / 0.5)
        a_out = ease((t - (ps(9) - 0.6)) / 0.5)
        a = a_in * (1 - a_out)
        if a <= 0: continue
        ghost = (0.62, 0.58, 0.52)
        ctx.save()
        g = cairo.RadialGradient(x, 1380, 10, x, 1380, 200); g.add_color_stop_rgba(0, 0.9, 0.85, 0.75, 0.18 * a); g.add_color_stop_rgba(1, 0.9, 0.85, 0.75, 0)
        ctx.set_source(g); ctx.arc(x, 1380, 200, 0, 2 * math.pi); ctx.fill()
        human(ctx, x, 1505, sc, kind, col=ghost, a=0.55 * a)
        ctx.restore()
    ctx.restore()
    drift_fog(ctx, 1450, 120, 0.2, t, 35)
    if t < ps(8):
        a = ease((t - ps(7) - 0.3) / 0.4)
        title(ctx, 'NO ONE ABOARD', 560, 76, a)

def davit(ctx, x, flip):
    ctx.set_line_width(14); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(x, 1520); ctx.line_to(x, 1000); ctx.curve_to(x, 900, x + flip * 40, 860, x + flip * 140, 860); ctx.stroke()
    ctx.set_line_width(3); ctx.move_to(x + flip * 140, 860); ctx.line_to(x + flip * 140 + 6 * math.sin(time_g * 1.3), 1250); ctx.stroke()

time_g = 0.0
def scene_F(ctx, t, s, e):
    global time_g; time_g = t
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.1, 1.15, e - s)
    if t < ps(10) - 0.1:
        sea(ctx, t, 1350, rows=6, moon_x=780)
        ctx.set_source_rgb(*SIL); ctx.rectangle(-100, 1520, W + 200, 600); ctx.fill()
        davit(ctx, 200, 1); davit(ctx, 880, -1)
        # chocks where the boat sat
        for cx in (360, 720): ctx.rectangle(cx - 40, 1480, 80, 45); ctx.fill()
        # red dashed outline: the missing boat
        k = ease((t - ps(9) - 0.8) / 0.5)
        ctx.save(); ctx.set_source_rgba(*RED, k); ctx.set_line_width(7); ctx.set_dash([26, 18], -t * 30)
        ctx.move_to(220, 1350); ctx.line_to(860, 1350); ctx.curve_to(830, 1440, 760, 1480, 680, 1480); ctx.line_to(400, 1480); ctx.curve_to(320, 1480, 250, 1440, 220, 1350); ctx.stroke()
        ctx.restore()
        if k > 0: title(ctx, 'MISSING', 1310, 60, k, col=RED)
    else:
        lt2 = t - ps(10)
        ctx.save(); push(ctx, lt2, e - ps(10), 1.0, 1.18, 300, 1400)
        ship(ctx, 840, 1330, 1.05, t, roll=0.04, rope=ease(lt2 / 2.0))
        sea(ctx, t, 1320, moon_x=780)
        # rope continues on the water surface (in front of swells)
        u = ease(lt2 / 2.0)
        ctx.set_source_rgb(*RED); ctx.set_line_width(8)
        ctx.move_to(840 - 470 * 1.05 - 140 * u * 1.05, 1350)
        for i in range(12):
            xx = 840 - 480 * 1.05 - 140 * u * 1.05 - i * 28 * u
            ctx.line_to(xx, wave_y(xx, t, 1360 + i * 10, 8))
        ctx.stroke()
        ctx.restore()
        drift_fog(ctx, 1330, 90, 0.18, t)

def scene_G(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, CHART, lt, 1.0, 1.08, e - s, dy=60)
    # candle glow on chart
    lantern(ctx, 900, 1450, t, 2, r=600, a=0.25)
    # Azores marker
    k1 = ease(lt / 0.5)
    ctx.set_source_rgba(*RED, k1); ctx.arc(*AZ, 14, 0, 2 * math.pi); ctx.fill()
    ctx.set_line_width(4); ctx.arc(*AZ, 26 + 6 * math.sin(t * 4), 0, 2 * math.pi); ctx.stroke()
    title_xy = ps(12) - 0.1
    if t > title_xy:
        u = ease((t - title_xy) / 1.6)
        ctx.save(); ctx.set_source_rgb(*RED); ctx.set_line_width(6); ctx.set_dash([18, 14])
        ctx.move_to(*AZ); ctx.line_to(AZ[0] + (FOUND[0] - AZ[0]) * u, AZ[1] + (FOUND[1] - AZ[1]) * u); ctx.stroke(); ctx.restore()
        if u > 0.95:
            # small ship icon at found point
            ship(ctx, FOUND[0], FOUND[1] + 10, 0.11, t, roll=0.02, col=(0.15, 0.09, 0.05), sail=(0.25, 0.17, 0.10))
        a = ease((t - title_xy - 0.3) / 0.4)
        title(ctx, '~400 MILES', 300, 110, a, font='Anton', col=RED)
    # log book in the foreground (bottom), ink entry
    ctx.save(); ctx.translate(W / 2, 1680); ctx.rotate(-0.05)
    ctx.set_source_rgb(0.12, 0.07, 0.04); ctx.rectangle(-420, -150, 840, 330); ctx.fill()
    ctx.set_source_rgb(0.78, 0.68, 0.50); ctx.rectangle(-400, -135, 390, 300); ctx.fill(); ctx.rectangle(10, -135, 390, 300); ctx.fill()
    ctx.set_source_rgba(0.2, 0.12, 0.06, 0.8); ctx.set_line_width(3)
    rng = random.Random(11)
    for r in range(8):
        for side in (-1, 1):
            if side == 1 and r > 2: continue
            x0 = -380 if side < 0 else 30
            ctx.move_to(x0, -100 + r * 34)
            xx = x0
            while xx < x0 + rng.uniform(260, 350):
                xx += 8; ctx.line_to(xx, -100 + r * 34 + rng.uniform(-4, 4))
            ctx.stroke()
    ctx.select_font_face('Cinzel', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(30)
    ctx.set_source_rgba(0.2, 0.12, 0.06, 0.9); ctx.move_to(40, 70); ctx.show_text('25 NOV 1872')
    ctx.restore()

def scene_H(ctx, t, s, e):
    lt = t - s
    bg_paint(ctx, NIGHT, lt, 1.0, 1.1, e - s)
    u = lt / (e - s)
    # the ship sails away into fog, slowly fading
    fade = 1 - 0.75 * ease((lt - 2.5) / 6.0)
    col = tuple(SIL[i] * fade + 0.24 * (1 - fade) for i in range(3))
    ship(ctx, 640 - 160 * u, 1255, 0.55 - 0.18 * u, t, roll=0.05, col=col, sail=tuple(0.13 * fade + 0.25 * (1 - fade) for _ in range(3)))
    sea(ctx, t, 1250, moon_x=780)
    drift_fog(ctx, 1240, 140, 0.3 + 0.2 * ease(lt / 6), t, 25)
    if t > ps(15) - 0.1:
        a = ease((t - ps(15)) / 0.5)
        title(ctx, 'MARY CELESTE', 540, 92, a)
        title(ctx, 'never solved', 620, 46, a, col=(0.8, 0.75, 0.65))

DRAW = {'A': scene_A, 'B': scene_B, 'C': scene_C, 'D': scene_D, 'E': scene_E, 'F': scene_F, 'G': scene_G, 'H': scene_H}

def frame(ctx, name, t, s, e):
    ctx.save(); DRAW[name](ctx, t, s, e); ctx.restore()
    vignette(ctx, 0.8)
    fl = 0.04 * (math.sin(t * 17) * math.sin(t * 5.3) + 1)
    ctx.set_source_rgba(0, 0, 0, fl); ctx.paint()
    k = t - s
    if k < 0.15 and name != 'A': ctx.set_source_rgba(0, 0, 0, 1 - k / 0.15); ctx.paint()
    if name == 'A' and k < 0.4: ctx.set_source_rgba(0, 0, 0, 1 - k / 0.4); ctx.paint()
    if t > TOTAL - 0.6: ctx.set_source_rgba(0, 0, 0, (t - (TOTAL - 0.6)) / 0.6); ctx.paint()
    draw_captions(ctx, t)

def load_bgs():
    global NIGHT, CABIN, CHART
    NIGHT = night_bg(); CABIN = cabin_bg(); CHART = chart_bg()

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
