"""Train the original 321 AI image diffusion model on a local image folder."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path

def main(argv=None):
    p=argparse.ArgumentParser(prog="321 ai train-images")
    p.add_argument("images",help="Folder containing licensed training images")
    p.add_argument("--output",default="321-image-model")
    p.add_argument("--steps",type=int,default=20000)
    p.add_argument("--batch",type=int,default=16)
    p.add_argument("--size",type=int,default=64,choices=(64,))
    p.add_argument("--device",default="auto",choices=("auto","cpu","cuda","mps"))
    args=p.parse_args(argv)
    if not 100<=args.steps<=1_000_000 or not 1<=args.batch<=128:
        print("Nieprawidłowy zakres kroków lub batch."); return 2
    try:
        import torch
        from torch.utils.data import DataLoader, Dataset
        from PIL import Image
        from .ai_image_model import ImageUNet, cosine_beta_schedule
    except ImportError as exc:
        print("Wymagane: pip install torch pillow"); print(exc); return 2
    class Images(Dataset):
        def __init__(self,root):
            self.files=[x for x in Path(root).rglob("*") if x.suffix.lower() in {".png",".jpg",".jpeg",".webp"}]
            if not self.files: raise ValueError("Folder nie zawiera obrazów PNG/JPG/WEBP.")
        def __len__(self): return len(self.files)
        def __getitem__(self,index):
            with Image.open(self.files[index]) as im:
                im=im.convert("RGB").resize((64,64),Image.Resampling.LANCZOS)
                import numpy as np
                arr=np.asarray(im,dtype="float32")/127.5-1
                return torch.from_numpy(arr).permute(2,0,1)
    try: dataset=Images(args.images)
    except Exception as exc: print(exc); return 2
    device="cuda" if args.device=="auto" and torch.cuda.is_available() else "mps" if args.device=="auto" and getattr(torch.backends,"mps",None) and torch.backends.mps.is_available() else "cpu" if args.device=="auto" else args.device
    if device=="cuda" and not torch.cuda.is_available(): print("CUDA niedostępne"); return 2
    loader=DataLoader(dataset,batch_size=args.batch,shuffle=True,num_workers=0,drop_last=True)
    if len(loader)==0: print("Za mało obrazów na jeden batch. Zmniejsz batch."); return 2
    model=ImageUNet().to(device); opt=torch.optim.AdamW(model.parameters(),lr=2e-4)
    steps=1000; betas=cosine_beta_schedule(steps,device); alphas=1-betas; abar=torch.cumprod(alphas,0)
    out=Path(args.output).expanduser().resolve(); out.mkdir(parents=True,exist_ok=True)
    iterator=iter(loader); started=time.monotonic(); model.train()
    for step in range(1,args.steps+1):
        try: clean=next(iterator).to(device)
        except StopIteration: iterator=iter(loader); clean=next(iterator).to(device)
        t=torch.randint(0,steps,(clean.shape[0],),device=device)
        noise=torch.randn_like(clean)
        a=abar[t][:,None,None,None]
        noisy=a.sqrt()*clean+(1-a).sqrt()*noise
        predicted=model(noisy,t.float())
        loss=torch.nn.functional.mse_loss(predicted,noise)
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
        if step%100==0 or step==1 or step==args.steps:
            print(f"Krok {step:,}/{args.steps:,} | loss {loss.item():.5f} | {time.monotonic()-started:.0f}s",flush=True)
        if step%500==0 or step==args.steps:
            torch.save({"state_dict":model.state_dict(),"base":64,"timesteps":steps,"size":64,"step":step},out/"image_model.pt")
    (out/"image_model_info.json").write_text(json.dumps({"architecture":"321-ImageDDPM-U-Net","trained_from_scratch":True,"image_size":64,"training_images":len(dataset),"steps":args.steps,"device":device,"limitations":"Experimental unconditional image model; output quality depends on dataset and training scale."},indent=2),encoding="utf-8")
    print(f"Zapisano wagi: {out/'image_model.pt'}")
    return 0
if __name__=="__main__": raise SystemExit(main())
