"""Generate fresh samples from a locally trained 321 AI DDPM checkpoint."""
from __future__ import annotations
import argparse,math
from pathlib import Path
import torch
from PIL import Image
from .image_trainer import Net,SIZE,STEPS
def main():
 p=argparse.ArgumentParser(); p.add_argument("--model",required=True); p.add_argument("--out",required=True); p.add_argument("--count",type=int,default=4); a=p.parse_args()
 if not 1<=a.count<=64: raise SystemExit("count 1-64")
 dev="cuda" if torch.cuda.is_available() else "cpu"; ck=torch.load(a.model,map_location=dev,weights_only=False)
 net=Net().to(dev); net.load_state_dict(ck["ema"]); net.eval()
 beta=torch.linspace(1e-4,.02,STEPS,device=dev); al=1-beta; ab=al.cumprod(0)
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 with torch.no_grad():
  x=torch.randn(a.count,3,SIZE,SIZE,device=dev)
  for t in reversed(range(STEPS)):
   tt=torch.full((a.count,),t,device=dev,dtype=torch.long)
   eps=net(x,tt); x=(x-eps*(1-al[t])/torch.sqrt(1-ab[t]))/torch.sqrt(al[t])
   if t>0: x+=torch.sqrt(beta[t])*torch.randn_like(x)
   if t%50==0: print(f"Sampling {t}/{STEPS}",flush=True)
  x=((x.clamp(-1,1)+1)*127.5).byte().permute(0,2,3,1).cpu().numpy()
 for i,img in enumerate(x): Image.fromarray(img).save(out/f"321_generated_{i+1:03d}.png")
 print(f"Zapisano {a.count} obrazów w {out}")
if __name__=="__main__":main()
