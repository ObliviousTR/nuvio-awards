"""Approximate Nuvio TV home hero (960x540 dp): partial() is the default layout (a 72%-wide box cropped from its top
right, the left faded), full() the full-screen backdrop setting. For review sheets only."""
from PIL import Image, ImageDraw
SW,SH=960,540; BW,BH=691,307; BX=SW-BW+48
def grad(w,h,fe):
    m=Image.new('L',(w,1)); px=m.load(); stops=[(0,255),(0.22,219),(0.46,143),(0.76,41),(1,0)]
    for x in range(w):
        f=min(1,x/(fe*w))
        for (a,va),(b,vb) in zip(stops,stops[1:]):
            if a<=f<=b: px[x,0]=int(va+(vb-va)*(f-a)/(b-a)); break
    return m.resize((w,h))
G1=grad(SW,SH,0.45); G2=grad(SW,SH,0.65)
BG=(13,13,16)
def partial(hero, logo=None):
    scr=Image.new('RGB',(SW,SH),BG); im=hero.convert('RGB')
    r=max(BW/im.width,BH/im.height); im=im.resize((round(im.width*r),round(im.height*r)),Image.LANCZOS)
    scr.paste(im.crop((im.width-BW,0,im.width,BH)),(BX,0))
    scr=Image.composite(Image.new('RGB',(SW,SH),BG),scr,G1)
    fade=Image.linear_gradient('L').resize((SW,80)); scr.paste(BG,(0,BH-80,SW,BH),fade); scr.paste(BG,(0,BH,SW,SH))
    if logo is not None:
        lg=logo.copy(); lg.thumbnail((220,100),Image.LANCZOS); scr.paste(lg,(48,BH-60-lg.height),lg)
    rows(scr); return scr
def full(hero, logo=None):
    im=hero.convert('RGB').resize((SW,SH),Image.LANCZOS)
    scr=Image.composite(Image.new('RGB',(SW,SH),BG),im,G2)
    fade=Image.linear_gradient('L').resize((SW,260)); scr.paste(BG,(0,SH-260,SW,SH),fade)
    if logo is not None:
        lg=logo.copy(); lg.thumbnail((220,100),Image.LANCZOS); scr.paste(lg,(48,BH-60-lg.height),lg)
    rows(scr); return scr
def rows(scr):
    d=ImageDraw.Draw(scr)
    for i in range(5): d.rounded_rectangle((48+i*176,BH+40,48+i*176+160,BH+40+90),radius=8,fill=(45,45,52))
