import numpy as np, soundfile as sf
import sys
sr=44100; dur=float(sys.argv[1]) if len(sys.argv)>1 else 57.0; N=int(sr*dur); y=np.zeros(N); 
def note(f): return 440*2**((f-69)/12)
def mbox(t0,m,amp=0.25,dec=1.8):
    n=int(sr*2.5); t=np.arange(n)/sr; env=np.exp(-t*dec)*(1-np.exp(-t*400))
    f=note(m); s=(np.sin(2*np.pi*f*t)+0.35*np.sin(2*np.pi*f*2.01*t)*np.exp(-t*3)+0.15*np.sin(2*np.pi*f*3.02*t)*np.exp(-t*5))
    s+=0.6*np.sin(2*np.pi*f*1.004*t)  # detune
    i=int(t0*sr)
    if i>=N: return
    j=min(N,i+n); y[i:j]+=amp*(s*env)[:j-i]
beat=60/80; bar=3*beat
prog=[(57,[60,64,69]),(50,[62,65,69]),(52,[59,64,68]),(57,[60,64,69]),(53,[60,65,69]),(50,[62,65,69]),(52,[59,62,68]),(52,[59,64,68])]
mel=[[76,74,72],[74,72,69],[71,68,64],[69,None,None],[72,74,76],[77,76,74],[71,74,68],[69,None,None]]
nb=int(dur/bar)+1
for b in range(nb):
    t0=b*bar+0.3
    root,ch=prog[b%8]
    mbox(t0,root+12,0.18,1.2)
    for k in (1,2): 
        for m in ch: mbox(t0+k*beat,m+12,0.07,2.5)
    if b>=1:
        for k,m in enumerate(mel[b%8]):
            if m: mbox(t0+k*beat+0.01*np.random.rand(),m+12,0.14,1.4)
# drone
t=np.arange(N)/sr
dr=0.18*np.sin(2*np.pi*55*t)+0.1*np.sin(2*np.pi*55.4*t)+0.06*np.sin(2*np.pi*82.5*t)
dr*=0.6+0.4*np.sin(2*np.pi*0.07*t)
y+=dr*np.clip(t/3,0,1)
# slow detuned wobble (warped tape feel) via fade
y=y/np.abs(y).max()*0.8
fade=np.ones(N); fo=int(2.5*sr); fade[-fo:]=np.linspace(1,0,fo)
sf.write('music_raw.wav',(y*fade).astype(np.float32),sr)
