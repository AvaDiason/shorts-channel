import cairo, math, render
S=800
surf=cairo.ImageSurface(cairo.FORMAT_ARGB32,S,S); ctx=cairo.Context(surf)
g=cairo.LinearGradient(0,0,0,S); g.add_color_stop_rgb(0,0.05,0.05,0.08); g.add_color_stop_rgb(1,0.22,0.15,0.13)
ctx.set_source(g); ctx.paint()
# moon behind spire
ctx.save(); ctx.translate(-140,-170); render.moon(ctx,540,420,120); ctx.restore()
# spire silhouette
ctx.set_source_rgb(0.02,0.02,0.03)
ctx.move_to(330,620); ctx.line_to(330,330); ctx.line_to(400,90); ctx.line_to(470,330); ctx.line_to(470,620); ctx.fill()
ctx.rectangle(396,40,8,60); ctx.fill(); ctx.rectangle(378,58,44,7); ctx.fill()
# rooftops
ctx.move_to(0,640)
for x,h in [(0,560),(90,500),(180,575),(250,520),(330,600),(470,600),(540,510),(630,570),(720,505),(800,560)]: ctx.line_to(x,h)
ctx.line_to(800,800); ctx.line_to(0,800); ctx.fill()
# red shoe
render.shoe(ctx,400,690,1.45,1)
g=cairo.RadialGradient(S/2,S/2,S*0.3,S/2,S/2,S*0.55); g.add_color_stop_rgba(0,0,0,0,0); g.add_color_stop_rgba(1,0,0,0,0.6)
ctx.set_source(g); ctx.paint()
surf.write_to_png('midnight_archives_avatar.png')
