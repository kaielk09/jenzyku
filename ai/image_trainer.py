"""Small 321-owned DCGAN training pipeline from a local image folder.
Requires PyTorch and Pillow. No image-generation API or pretrained weights.
"""
from __future__ import annotations
import argparse, json, random, time
from pathlib import Path
from PIL import Image
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader

IMG_SIZE=64
Z_DIM=128

class ImageFolderDataset(Dataset):
 def __init__(self, folder):
  self.paths=[p for p in Path(folder).rglob("*") if p.suffix.lower() in (".png",".jpg",".jpeg",".bmp",".webp")]
  if not self.paths: raise ValueError("Folder nie zawiera obsługiwanych obrazów.")
 def __len__(self): return len(self.paths)
 def __getitem__(self,index):
  with Image.open(self.paths[index]) as im:
   im=im.convert("RGB").resize((IMG_SIZE,IMG_SIZE))
   # normalize [-1, 1], CHW
   data=torch.tensor(list(im.getdata()),dtype=torch.float32).reshape(IMG_SIZE,IMG_SIZE,3).permute(2,0,1)
   return data/127.5-1

class Generator(nn.Module):
 def __init__(self,z=Z_DIM):
  super().__init__()
  self.net=nn.Sequential(
   nn.ConvTranspose2d(z,512,4,1,0,bias=False),nn.BatchNorm2d(512),nn.ReLU(True),
   nn.ConvTranspose2d(512,256,4,2,1,bias=False),nn.BatchNorm2d(256),nn.ReLU(True),
   nn.ConvTranspose2d(256,128,4,2,1,bias=False),nn.BatchNorm2d(128),nn.ReLU(True),
   nn.ConvTranspose2d(128,64,4,2,1,bias=False),nn.BatchNorm2d(64),nn.ReLU(True),
   nn.ConvTranspose2d(64,3,4,2,1,bias=False),nn.Tanh())
 def forward(self,z): return self.net(z)

class Discriminator(nn.Module):
 def __init__(self):
  super().__init__()
  self.net=nn.Sequential(
   nn.Conv2d(3,64,4,2,1,bias=False),nn.LeakyReLU(.2,inplace=True),
   nn.Conv2d(64,128,4,2,1,bias=False),nn.BatchNorm2d(128),nn.LeakyReLU(.2,inplace=True),
   nn.Conv2d(128,256,4,2,1,bias=False),nn.BatchNorm2d(256),nn.LeakyReLU(.2,inplace=True),
   nn.Conv2d(256,512,4,2,1,bias=False),nn.BatchNorm2d(512),nn.LeakyReLU(.2,inplace=True),
   nn.Conv2d(512,1,4,1,0,bias=False),nn.Sigmoid())
 def forward(self,x): return self.net(x).view(-1)

def save_checkpoint(path,payload):
 path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(".tmp")
 torch.save(payload,temp); temp.replace(path)

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--images",required=True); parser.add_argument("--out",required=True)
 parser.add_argument("--steps",type=int,default=5000); parser.add_argument("--batch",type=int,default=16)
 args=parser.parse_args()
 if args.steps<1 or args.steps>500000: raise SystemExit("Steps: 1-500000")
 data=ImageFolderDataset(args.images)
 device="cuda" if torch.cuda.is_available() else "cpu"
 effective_batch=min(args.batch,len(data))
 dl=DataLoader(data,batch_size=effective_batch,shuffle=True,drop_last=True,num_workers=0)
 if len(dl)==0: raise SystemExit("Za mało obrazów na wybrany batch; zmniejsz batch lub dodaj obrazy.")
 out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
 gen,disc=Generator().to(device),Discriminator().to(device)
 optg=torch.optim.Adam(gen.parameters(),lr=0.0002,betas=(0.5,0.999))
 optd=torch.optim.Adam(disc.parameters(),lr=0.0002,betas=(0.5,0.999))
 lossfn=nn.BCELoss(); start=0
 checkpoint=out/"checkpoint.pt"
 if checkpoint.exists():
  ck=torch.load(checkpoint,map_location=device,weights_only=True)
  gen.load_state_dict(ck["gen"]); disc.load_state_dict(ck["disc"])
  optg.load_state_dict(ck["optg"]); optd.load_state_dict(ck["optd"]); start=int(ck["step"])
  print(f"Kontynuacja treningu obrazów od kroku {start}")
 fixed=torch.randn(16,Z_DIM,1,1,device=device)
 step=start; epoch=0
 print(f"321 AI Images | {len(data)} obrazów | {device} | trening do kroku {args.steps}")
 while step<args.steps:
  for real in dl:
   if step>=args.steps: break
   real=real.to(device); n=real.size(0)
   # discriminator update
   disc.zero_grad(set_to_none=True)
   real_pred=disc(real); real_loss=lossfn(real_pred,torch.ones(n,device=device)*0.9)
   noise=torch.randn(n,Z_DIM,1,1,device=device); fake=gen(noise).detach()
   fake_loss=lossfn(disc(fake),torch.zeros(n,device=device))
   dloss=real_loss+fake_loss; dloss.backward(); optd.step()
   # generator update
   gen.zero_grad(set_to_none=True)
   noise=torch.randn(n,Z_DIM,1,1,device=device)
   gl=lossfn(disc(gen(noise)),torch.ones(n,device=device)); gl.backward(); optg.step()
   step+=1
   if step%100==0 or step==args.steps:
    save_checkpoint(checkpoint,{"gen":gen.state_dict(),"disc":disc.state_dict(),"optg":optg.state_dict(),"optd":optd.state_dict(),"step":step,"z_dim":Z_DIM,"image_size":IMG_SIZE})
    gen.eval()
    with torch.no_grad():
     sample=((gen(fixed).cpu().clamp(-1,1)+1)*127.5).byte().permute(0,2,3,1).numpy()
     # save preview sheet as individual sample PNGs
     sample_dir=out/"samples"; sample_dir.mkdir(exist_ok=True)
     for i,img in enumerate(sample[:4]): Image.fromarray(img).save(sample_dir/f"sample_{i}.png")
    gen.train()
    print(f"step {step}/{args.steps} | D {dloss.item():.3f} | G {gl.item():.3f}",flush=True)
  epoch+=1
 gen.cpu().eval()
 save_checkpoint(out/"generator.pt",{"state_dict":gen.state_dict(),"z_dim":Z_DIM,"image_size":IMG_SIZE,"steps":step})
 (out/"image_model_info.json").write_text(json.dumps({"model":"321-DCGAN","trained_from_scratch":True,"steps":step,"images":len(data),"size":IMG_SIZE,"device":device},indent=2),encoding="utf-8")
 print("Trening zakończony. Generator zapisany:",out/"generator.pt")

if __name__=="__main__": main()
