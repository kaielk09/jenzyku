"""Configurable 321 TinyGPT trainer with validation and resumable checkpoints."""
from __future__ import annotations
import json, sys, time
from pathlib import Path

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        print("Użycie: 321 ai train ścieżka/do/projektu"); return 2
    project=Path(args[0]).expanduser().resolve()
    cfg_path,dataset=project/"config.json",project/"dataset.txt"
    if not cfg_path.is_file() or not dataset.is_file():
        print("Brak config.json lub dataset.txt."); return 2
    cfg=json.loads(cfg_path.read_text(encoding="utf-8"))
    raw=dataset.read_text(encoding="utf-8")
    data="\n".join(line.rstrip() for line in raw.splitlines() if line.strip() and not line.lstrip().startswith("#")).encode("utf-8")
    if len(data)<2048:
        print("Zbiór danych jest za mały. Minimum techniczne: 2048 bajtów; do dobrego chatbota potrzeba znacznie więcej."); return 2
    try:
        import torch
        from torch.nn import functional as F
        try: from .ai_model import TinyGPT
        except ImportError: from code321.ai_model import TinyGPT
    except ImportError as exc:
        print("Brak PyTorch. Zainstaluj: python -m pip install torch"); print(exc); return 2
    steps=int(cfg.get("training_steps",10000)); width=int(cfg.get("width",256))
    layers=int(cfg.get("layers",6)); heads=int(cfg.get("heads",8))
    context=int(cfg.get("context",256)); batch=int(cfg.get("batch_size",8))
    lr=float(cfg.get("learning_rate",0.0003))
    if not (1<=steps<=1000000 and 64<=width<=1024 and 1<=layers<=24 and 1<=heads<=16 and width%heads==0 and 32<=context<=1024 and 1<=batch<=32 and 0.00001<=lr<=0.01):
        print("Nieprawidłowe lub zbyt duże parametry modelu."); return 2
    if len(data)<=context+2:
        print("Zbiór danych jest krótszy niż kontekst modelu."); return 2
    device="cuda" if torch.cuda.is_available() else "cpu"
    if device=="cuda":
        try: torch.cuda.set_per_process_memory_fraction(0.85)
        except (AttributeError,RuntimeError): pass
    torch.manual_seed(321)
    ids=torch.tensor(list(data),dtype=torch.long)
    split=max(context+2,int(len(ids)*0.95))
    train_ids=ids[:split]; val_ids=ids[split:]
    if len(val_ids)<context+2: val_ids=train_ids[-min(len(train_ids),context*4):]
    model=TinyGPT(width=width,layers=layers,heads=heads,context=context).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=0.1)
    ckpt=project/"checkpoints"/"latest.pt"; ckpt.parent.mkdir(parents=True,exist_ok=True)
    model_cfg={"vocab_size":256,"width":width,"layers":layers,"heads":heads,"context":context}
    start=0
    if ckpt.exists():
        try:
            saved=torch.load(ckpt,map_location=device,weights_only=True)
            if saved.get("config")==model_cfg:
                model.load_state_dict(saved["state_dict"]); optimizer.load_state_dict(saved["optimizer"]); start=int(saved.get("step",0))
                print(f"Wznowiono trening od kroku {start}.")
        except Exception as exc: print(f"Checkpoint nie został użyty: {exc}")
    def batch_data(source):
        starts=torch.randint(0,len(source)-context-1,(batch,))
        x=torch.stack([source[i:i+context] for i in starts]).to(device)
        y=torch.stack([source[i+1:i+context+1] for i in starts]).to(device)
        return x,y
    def validate():
        model.eval()
        with torch.no_grad():
            x,y=batch_data(val_ids); score=F.cross_entropy(model(x).reshape(-1,256),y.reshape(-1)).item()
        model.train(); return score
    model.train(); started=time.time()
    params=sum(p.numel() for p in model.parameters())
    print(f"321 AI | {cfg.get('name',project.name)} | {device} | {params:,} parametrów")
    print(f"Dane: {len(data):,} bajtów | trening 95% | walidacja 5% | cel {steps:,} kroków")
    for step in range(start,steps):
        x,y=batch_data(train_ids); logits=model(x)
        loss=F.cross_entropy(logits.reshape(-1,256),y.reshape(-1))
        optimizer.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); optimizer.step()
        interval=max(1,min(500,steps//50))
        if (step+1)%interval==0 or step==0 or step+1==steps:
            val=validate()
            print(f"Krok {step+1:,}/{steps:,} | train loss {loss.item():.4f} | val loss {val:.4f} | {time.time()-started:.0f}s",flush=True)
            torch.save({"state_dict":model.state_dict(),"optimizer":optimizer.state_dict(),"step":step+1,"config":model_cfg},ckpt)
    model_dir=project/"model"; model_dir.mkdir(exist_ok=True)
    torch.save({"state_dict":model.cpu().state_dict(),"config":model_cfg},model_dir/"model.pt")
    info={"name":cfg.get("name",project.name),"architecture":"321-TinyGPT (byte-level Transformer)",
          "trained_from_scratch":True,"training_steps":steps,"training_device":device,
          "dataset_bytes":len(data),"parameters":params,"model_config":model_cfg,
          "chat_format":"Użytkownik: ...\\nAI: ..."}
    (model_dir/"model_info.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
    (project/"status.json").write_text(json.dumps({"status":"trained","completed_steps":steps},indent=2),encoding="utf-8")
    print(f"\nGotowe. Model zapisano w: {model_dir}\nTest: 321 ai chat {project}")
    return 0

if __name__=="__main__": raise SystemExit(main())
