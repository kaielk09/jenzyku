"""321 AI one-click image training: collect a Commons dataset, then train DDPM."""
from __future__ import annotations
import argparse
from pathlib import Path
from .image_dataset import collect
from .image_trainer import main as trainer_main
import sys
def run():
 p=argparse.ArgumentParser(); p.add_argument("--category",default="random"); p.add_argument("--count",type=int,default=100); p.add_argument("--steps",type=int,default=8000); p.add_argument("--batch",type=int,default=8); p.add_argument("--out",required=True); a=p.parse_args()
 root=Path(a.out); ds=root/"dataset"; print("=== 321 AI • AUTOMATYCZNE DATASETOWANIE ===",flush=True)
 got=collect(a.category,a.count,ds)
 if got<8: raise SystemExit("Dataset za mały. Zmienić kategorię albo spróbować później.")
 print("=== DATASET GOTOWY • START DDPM ===",flush=True)
 sys.argv=["image_trainer","--images",str(ds),"--out",str(root/"training"),"--steps",str(a.steps),"--batch",str(a.batch)]
 trainer_main()
if __name__=="__main__":run()
