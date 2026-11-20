"""321 AI Images: from-scratch DDPM with residual U-Net, EMA and resume support."""
from __future__ import annotations
import argparse,json,math,random
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset,DataLoader
SIZE=64; STEPS=500; C=48
class Images(Dataset):
 def __init__(self,p):
  self.files=[x for x in Path(p).rglob("*") if x.suffix.lower() in (".png",".jpg",".jpeg",".webp",".bmp")]
  if not self.files: raise RuntimeError("Dataset nie ma obrazów.")
 def __len__(self): return len(self.files)
 def __getitem__(self,i):
  with Image.open(self.files[i]) as im: x=torch.from_numpy(np.array(im.convert("RGB").resize((SIZE,SIZE),Image.Resampling.LANCZOS))).permute(2,0,1).float()/127.5-1
  if random.random()<.5:x=x.flip(-1)
  return x
def t_embed(t,d):
 half=d//2; f=torch.exp(-math.log(10000)*torch.arange(half,device=t.device).float()/max(half-1,1)); x=t.float()[:,None]*f
 return torch.cat([x.sin(),x.cos()],-1)
class Res(nn.Module):
 def __init__(self,a,b,td):
  super().__init__(); self.n1=nn.GroupNorm(8,a); self.c1=nn.Conv2d(a,b,3,padding=1); self.tp=nn.Linear(td,b); self.n2=nn.GroupNorm(8,b); self.c2=nn.Conv2d(b,b,3,padding=1); self.skip=nn.Conv2d(a,b,1) if a!=b else nn.Identity()
 def forward(self,x,t):
  h=self.c1(F.silu(self.n1(x))); h=h+self.tp(t)[:,:,None,None]; return self.c2(F.silu(self.n2(h)))+self.skip(x)
class Net(nn.Module):
 def __init__(self):
  super().__init__(); td=C*4; self.te=nn.Sequential(nn.Linear(C,td),nn.SiLU(),nn.Linear(td,td)); self.i=nn.Conv2d(3,C,3,padding=1)
  self.r1=Res(C,C,td); self.d1=nn.Conv2d(C,2*C,4,2,1); self.r2=Res(2*C,2*C,td); self.d2=nn.Conv2d(2*C,4*C,4,2,1); self.r3=Res(4*C,4*C,td); self.d3=nn.Conv2d(4*C,4*C,4,2,1); self.m1=Res(4*C,4*C,td); self.m2=Res(4*C,4*C,td)
  self.u3=Res(8*C,4*C,td); self.u2=Res(6*C,2*C,td); self.u1=Res(3*C,C,td); self.o=nn.Sequential(nn.GroupNorm(8,C),nn.SiLU(),nn.Conv2d(C,3,3,padding=1))
 def forward(self,x,t):
  e=self.te(t_embed(t,C)); a=self.r1(self.i(x),e); b=self.r2(self.d1(a),e); c=self.r3(self.d2(b),e); h=self.m2(self.m1(self.d3(c),e),e)
  h=self.u3(torch.cat([F.interpolate(h,size=c.shape[-2:],mode="nearest"),c],1),e); h=self.u2(torch.cat([F.interpolate(h,size=b.shape[-2:],mode="nearest"),b],1),e); h=self.u1(torch.cat([F.interpolate(h,size=a.shape[-2:],mode="nearest"),a],1),e); return self.o(h)
class EMA:
 def __init__(self,m): self.s={k:v.detach().clone() for k,v in m.state_dict().items()}
 @torch.no_grad()
 def update(self,m):
  for k,v in m.state_dict().items(): self.s[k].mul_(.999).add_(v.detach(),alpha=.001)
def save_grid(x,path):
 x=((x.detach().cpu().clamp(-1,1)+1)*127.5).byte().permute(0,2,3,1).numpy(); im=Image.new("RGB",(4*SIZE,4*SIZE))
 for i,a in enumerate(x[:16]): im.paste(Image.fromarray(a),(i%4*SIZE,i//4*SIZE))
 path.parent.mkdir(parents=True,exist_ok=True); im.save(path)
def main():
 p=argparse.ArgumentParser(); p.add_argument("--images",required=True); p.add_argument("--out",required=True); p.add_argument("--steps",type=int,default=8000); p.add_argument("--batch",type=int,default=8); a=p.parse_args()
 if not 1<=a.steps<=300000 or a.batch not in (2,4,8,16,32): raise SystemExit("Nieprawidłowe parametry.")
 ds=Images(a.images); dev="cuda" if torch.cuda.is_available() else "cpu"; dl=DataLoader(ds,batch_size=min(a.batch,len(ds)),shuffle=True,num_workers=0,pin_memory=dev=="cuda")
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True); m=Net().to(dev); opt=torch.optim.AdamW(m.parameters(),lr=2e-4,weight_decay=1e-4); ema=EMA(m); scaler=torch.amp.GradScaler("cuda",enabled=dev=="cuda"); betas=torch.linspace(1e-4,.02,STEPS,device=dev); al=(1-betas); abar=al.cumprod(0); step=0; cp=out/"checkpoint.pt"
 if cp.exists():
  ck=torch.load(cp,map_location=dev,weights_only=False); m.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"]); ema.s=ck["ema"]; step=int(ck["step"]); print("Wznawiam od kroku",step)
 print(f"321 AI DDPM | {len(ds)} images | {dev} | steps target {a.steps}",flush=True); m.train()
 while step<a.steps:
  for x in dl:
   if step>=a.steps:break
   x=x.to(dev,non_blocking=True); t=torch.randint(STEPS,(len(x),),device=dev); n=torch.randn_like(x); q=abar[t][:,None,None,None]; noisy=q.sqrt()*x+(1-q).sqrt()*n
   with torch.autocast(device_type="cuda",dtype=torch.float16,enabled=dev=="cuda"): pred=m(noisy,t); loss=F.mse_loss(pred.float(),n)
   opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(m.parameters(),1.0); scaler.step(opt); scaler.update(); ema.update(m); step+=1
   if step%250==0 or step==a.steps:
    torch.save({"model":m.state_dict(),"opt":opt.state_dict(),"ema":ema.s,"step":step,"size":SIZE,"timesteps":STEPS},cp); print(f"step {step}/{a.steps} loss={loss.item():.4f}",flush=True)
  # cycle over dataset until requested step count
 torch.save({"ema":ema.s,"size":SIZE,"timesteps":STEPS,"trained_from_scratch":True,"steps":step},out/"image_model.pt")
 (out/"model_info.json").write_text(json.dumps({"architecture":"321-DDPM-ResidualUNet","steps":step,"images":len(ds),"resolution":SIZE,"diffusion_steps":STEPS,"device":dev},indent=2),encoding="utf-8")
 print("Checkpoint zapisany; samplowanie pełnego DDPM będzie osobnym modułem.")
if __name__=="__main__":main()
