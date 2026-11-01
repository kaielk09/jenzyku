"""Terminal text generation demo for the experimental 321 AI model."""
import sys
from pathlib import Path

def main():
    try: import torch
    except ImportError: print("Zainstaluj PyTorch: python -m pip install torch"); return 2
    p=Path(sys.argv[1]).resolve()
    saved=torch.load(p/"model"/"model.pt",map_location="cpu",weights_only=True)
    alphabet=saved["alphabet"]; enc={c:i for i,c in enumerate(alphabet)}; dec={i:c for i,c in enumerate(alphabet)}
    from torch import nn
    class Model(nn.Module):
        def __init__(self):
            super().__init__(); self.emb=nn.Embedding(len(alphabet),64); self.rnn=nn.GRU(64,128,batch_first=True); self.out=nn.Linear(128,len(alphabet))
        def forward(self,x):
            x,_=self.rnn(self.emb(x)); return self.out(x)
    model=Model(); model.load_state_dict(saved["state_dict"]); model.eval()
    print("321 AI — eksperymentalny generator tekstu. /exit kończy.")
    while True:
        prompt=input("Ty> ")
        if prompt.strip()=="/exit": break
        known=[c for c in prompt if c in enc]
        if not known: print("AI> Brak znanych znaków."); continue
        ids=torch.tensor([[enc[c] for c in known]])
        result=[]
        with torch.no_grad():
            for _ in range(240):
                nxt=int(model(ids[:,-128:])[:,-1,:].argmax(-1).item()); result.append(dec[nxt]); ids=torch.cat((ids,torch.tensor([[nxt]])),dim=1)
        print("AI> "+"".join(result))
    return 0
if __name__=="__main__": raise SystemExit(main())
