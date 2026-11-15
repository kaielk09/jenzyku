"""Sampling utility for the experimental 321 unconditional DDPM model."""
from __future__ import annotations
import argparse
from pathlib import Path

def generate(checkpoint: str | Path, output: str | Path, count: int=1, device: str="auto", seed: int|None=None):
    import torch
    from PIL import Image
    import numpy as np
    from .ai_image_model import ImageUNet, cosine_beta_schedule
    if not 1<=count<=16: raise ValueError("Liczba obrazów musi należeć do zakresu 1–16.")
    target=Path(checkpoint).expanduser().resolve()
    if target.is_dir(): target=target/"image_model.pt"
    if not target.is_file(): raise FileNotFoundError(f"Nie znaleziono checkpointu: {target}")
    if device=="auto": device="cuda" if torch.cuda.is_available() else "mps" if getattr(torch.backends,"mps",None) and torch.backends.mps.is_available() else "cpu"
    saved=torch.load(target,map_location=device,weights_only=True)
    steps=int(saved["timesteps"])
    model=ImageUNet(base=int(saved.get("base",64))).to(device)
    model.load_state_dict(saved["state_dict"]); model.eval()
    betas=cosine_beta_schedule(steps,device); alphas=1-betas; abar=torch.cumprod(alphas,0)
    previous=torch.cat((torch.ones(1,device=device),abar[:-1]))
    posterior_var=betas*(1-previous)/(1-abar)
    if seed is not None: torch.manual_seed(seed)
    out=Path(output).expanduser().resolve(); out.mkdir(parents=True,exist_ok=True)
    paths=[]
    with torch.inference_mode():
        for index in range(1,count+1):
            x=torch.randn(1,3,64,64,device=device)
            for i in reversed(range(steps)):
                t=torch.full((1,),float(i),device=device)
                eps=model(x,t)
                x=(x-(betas[i]/torch.sqrt(1-abar[i]))*eps)/torch.sqrt(alphas[i])
                if i>0: x=x+torch.sqrt(posterior_var[i])*torch.randn_like(x)
            arr=((x[0].clamp(-1,1)+1)*127.5).byte().permute(1,2,0).cpu().numpy()
            image=Image.fromarray(np.asarray(arr,dtype=np.uint8),"RGB")
            path=out/f"321-ai-image-{index:02d}.png"; image.save(path); paths.append(path)
    return paths

def main(argv=None):
    p=argparse.ArgumentParser(prog="321 ai generate-image")
    p.add_argument("checkpoint"); p.add_argument("--output",default="321-generated-images")
    p.add_argument("--count",type=int,default=1); p.add_argument("--device",choices=("auto","cpu","cuda","mps"),default="auto")
    p.add_argument("--seed",type=int)
    a=p.parse_args(argv)
    try:
        for path in generate(a.checkpoint,a.output,a.count,a.device,a.seed): print(f"Zapisano: {path}")
    except Exception as exc: print(f"Błąd generowania: {exc}"); return 2
    return 0
if __name__=="__main__": raise SystemExit(main())
