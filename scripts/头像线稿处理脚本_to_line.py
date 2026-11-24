import cv2, numpy as np, sys, os
from PIL import Image

def load_gray(p):
    im=cv2.imdecode(np.fromfile(p,dtype=np.uint8),cv2.IMREAD_COLOR)
    return im

def face_box(bgr):
    g=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
    cas=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    h,w=g.shape
    fs=cas.detectMultiScale(g,1.08,6,minSize=(int(min(h,w)*0.12),)*2)
    if len(fs)==0: return None
    # 取最大、最靠上的
    f=max(fs,key=lambda b:b[2]*b[3])
    return f

def crop_bust(bgr, fill=1.35, top_pad=0.07):
    """头+颈+衣领胸像：以人脸框为基准扩边"""
    fb=face_box(bgr)
    h,w=bgr.shape[:2]
    if fb is None:
        s=min(h,w); cx,cy=w//2,int(h*0.42); side=int(s*fill)
        x0,y0=cx-side//2, cy-side//2
    else:
        x,y,fw,fh=fb
        cx=x+fw//2; cy=y+int(fh*0.62)
        side=int(fw*fill*2.0)
        x0=cx-side//2; y0=cy-int(side*0.52)
    x0=max(0,x0); y0=max(0,y0); side=int(side)
    x1=min(w,x0+side); y1=min(h,y0+side)
    crop=bgr[y0:y1,x0:x1]
    # 补成正方形
    ch,cw=crop.shape[:2]; S=max(ch,cw)
    canvas=np.full((S,S,3),0,np.uint8)
    canvas[(S-ch)//2:(S-ch)//2+ch,(S-cw)//2:(S-cw)//2+cw]=crop
    return canvas

def xdog(gray, sigma=0.8, k=1.6, p=22, phi=0.017, eps=0.0025):
    g=np.float32(gray)/255.0
    g1=cv2.GaussianBlur(g,(0,0),sigma)
    g2=cv2.GaussianBlur(g,(0,0),sigma*k)
    d=g1-p*g2
    T=1.0+np.tanh(phi*(d-eps))
    line=np.clip((1.0-T)/ (T.max() if T.max()>0 else 1), 0, 1)
    return line

def to_line_rgba(bgr, size=192, boost=1.0, floor=0.06):
    sq=crop_bust(bgr)
    sq=cv2.resize(sq,(512,512),interpolation=cv2.INTER_AREA)
    g=cv2.cvtColor(sq,cv2.COLOR_BGR2GRAY)
    g=cv2.medianBlur(g,3)
    L=xdog(g)
    L=np.clip(L*boost,0,1)
    # 去掉极弱响应（纸纹噪点）
    a=(L**0.72)
    a=np.where(a<floor,0,a)
    a=(a*255).astype(np.uint8)
    rgba=np.zeros((512,512,4),np.uint8)
    rgba[...,0:3]=255
    rgba[...,3]=a
    img=Image.fromarray(rgba,'RGBA').resize((size,size),Image.LANCZOS)
    return img

if __name__=='__main__':
    src=sys.argv[1]; out=sys.argv[2]
    bgr=load_gray(src)
    img=to_line_rgba(bgr)
    img.save(out,'WEBP',quality=88,method=6)
    print(out, img.size, img.mode, os.path.getsize(out),'bytes')
