import sys, numpy as np, cv2
from rembg import new_session, remove
from PIL import Image
p=sys.argv[1]
im=Image.open(f"el/{p}.jpg").convert("RGB"); im.thumbnail((1280,1280))
out=remove(im,session=new_session("isnet-general-use"))
al=np.asarray(out.getchannel('A')).copy()
n,lab,st,_=cv2.connectedComponentsWithStats((al>40).astype(np.uint8))
if n>1:
    big=st[1:,cv2.CC_STAT_AREA].max(); keep=[i for i in range(1,n) if st[i,cv2.CC_STAT_AREA]>=0.06*big]; al[~np.isin(lab,keep)]=0
out.putalpha(Image.fromarray(al)); m=al>128
print(p,"top",round(m[:2].mean(),3),"L",round(m[:,:2].mean(),3),"R",round(m[:,-2:].mean(),3),"B",round(m[-2:].mean(),3),"area",round(m.mean(),3),flush=True)
out.save(f"el/{p}.png")
