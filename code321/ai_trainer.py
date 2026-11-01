"""Educational small character-level GRU trainer. Requires a user dataset and PyTorch."""
from __future__ import annotations
import json, sys
from pathlib import Path

def main():
    project=Path(sys.argv[1]).resolve()
    cfg=json.loads((project/"config.json").read_text(encoding="utf-8"))
    dataset=project/"dataset.txt"
    raw=dataset.read_text(encoding="utf-8")
    text="\n".join(x for x in raw.splitlines() if x.strip() and not x.lstrip().startswith("#"))
    if len(text)<200:
        print("321 AI: brak danych treningowych. Dodaj co najmniej 200 znaków do dataset.txt i uruchom trening ponownie.")
        print("Nie utworzono fikcyjnego modelu.")
        return 2
    try:
        import torch
        from torch import nn
    except ImportError:
        print("Brak PyTorch. Zainstaluj: python -m pip install torch")
        return 2
    device="cuda" if torch.cuda.is_available() else "cpu"
    if device=="cuda":
        try: torch.cuda.set_per_process_memory_fraction(0.50)
        except (AttributeError,RuntimeError): pass
    print(f"Urządzenie: {device}; karta wpisana w formularzu: {cfg['gpu_label']}")
    print("To mały model znakowy, nie ogólna sztuczna inteligencja. Kontroluj temperaturę urządzenia.")
    alphabet=sorted(set(text))
    if len(alphabet)<2: print("Dane muszą zawierać różne znaki."); return 2
    enc={c:i for i,c in enumerate(alphabet)}
    ids=torch.tensor([enc[c] for c in text],dtype=torch.long)
    class Model(nn.Module):
        def __init__(self):
            super().__init__(); self.emb=nn.Embedding(len(alphabet),64); self.rnn=nn.GRU(64,128,batch_first=True); self.out=nn.Linear(128,len(alphabet))
        def forward(self,x):
            x,_=self.rnn(self.emb(x)); return self.out(x)
    model=Model().to(device); opt=torch.optim.AdamW(model.parameters(),lr=0.001); loss_fn=nn.CrossEntropyLoss()
    steps=int(cfg["training_steps"]); seq=min(64,max(8,len(ids)//4)); batch=8
    model.train()
    for step in range(steps):
        starts=torch.randint(0,len(ids)-seq-1,(batch,))
        x=torch.stack([ids[s:s+seq] for s in starts]).to(device)
        y=torch.stack([ids[s+1:s+seq+1] for s in starts]).to(device)
        opt.zero_grad(set_to_none=True); loss=loss_fn(model(x).reshape(-1,len(alphabet)),y.reshape(-1)); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
        if (step+1)%max(1,steps//20)==0: print(f"Krok {step+1}/{steps} | loss={loss.item():.4f}")
    out=project/"model"; out.mkdir(exist_ok=True)
    torch.save({"state_dict":model.cpu().state_dict(),"alphabet":alphabet},out/"model.pt")
    (out/"model_info.json").write_text(json.dumps({"name":cfg["name"],"architecture":"character-GRU","steps":steps,"device":device,"dataset_characters":len(text)},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Model zapisany w: {out}")
    print("Model eksperymentalny; nie jest samodzielnym plikiem EXE ani pełnym chatbotem.")
    return 0
if __name__=="__main__": raise SystemExit(main())
