import sys; from PIL import Image
fs=sys.argv[2:]; ims=[Image.open(f).resize((360,640)) for f in fs]
g=Image.new('RGB',(360*5,640*((len(ims)+4)//5)))
for i,im in enumerate(ims): g.paste(im,((i%5)*360,(i//5)*640))
g.save(sys.argv[1],quality=85)
