import sys
from rembg import new_session, remove
from PIL import Image
import numpy as np
p=sys.argv[1]; model=sys.argv[2]
crops={"tos_02":(0,0,0.55,0.6),"tng_06":(0.5,0,1,1),"ds9_21":(0.12,0.04,0.5,0.62),"snw_09":(0.2,0,0.8,1),"dis_06":(0.3,0.02,0.75,1),"khan_04":(0.08,0,0.78,1)}
im=Image.open(f"el/{p}.jpg").convert("RGB")
if p in crops:
    a,b,c,d=crops[p]; W,H=im.size; im=im.crop((int(a*W),int(b*H),int(c*W),int(d*H)))
im.thumbnail((1100,1100))
out=remove(im,session=new_session(model),alpha_matting=(len(sys.argv)>3),alpha_matting_foreground_threshold=240,alpha_matting_background_threshold=15,alpha_matting_erode_size=8)
import cv2
al=np.asarray(out.getchannel('A')).copy()
n,lab,st,_=cv2.connectedComponentsWithStats((al>40).astype(np.uint8))
if n>1:
    big=st[1:,cv2.CC_STAT_AREA].max()
    keep=[i for i in range(1,n) if st[i,cv2.CC_STAT_AREA]>=0.08*big]
    al[~np.isin(lab,keep)]=0
out.putalpha(Image.fromarray(al))
m=al>128
print(p, out.size, "top",round(m[:2].mean(),3),"L",round(m[:,:2].mean(),3),"R",round(m[:,-2:].mean(),3),"B",round(m[-2:].mean(),3), flush=True)
out=out.crop(out.getchannel('A').point(lambda v:255 if v>16 else 0).getbbox()); out.save(f"el/{p}.png")
