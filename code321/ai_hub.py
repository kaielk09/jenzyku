"""Hugging Face dataset import and model publishing helpers."""
from __future__ import annotations
import json, os
from pathlib import Path

# Explicit allow-list; unknown/missing licenses are rejected by default.
ALLOWED_DATASET_LICENSES = {
    "mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "cc0-1.0",
    "cc-by-4.0", "cc-by-sa-4.0", "isc",
}

def _hub():
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError as exc:
        raise RuntimeError("Zainstaluj: pip install '321code-lang[huggingface]'") from exc
    return HfApi, create_repo

def publish_model(project: str | Path, repo_id: str, private: bool = True) -> str:
    root=Path(project).expanduser().resolve()
    model=root/"model"/"model.pt"
    if not model.is_file(): raise FileNotFoundError("Najpierw wytrenuj model — brakuje model/model.pt.")
    token=os.environ.get("HF_TOKEN","").strip()
    if not token: raise RuntimeError("Ustaw zmienną środowiskową HF_TOKEN. Token nie jest zapisywany w plikach projektu.")
    HfApi, create_repo=_hub()
    api=HfApi(token=token)
    create_repo(repo_id=repo_id,repo_type="model",private=private,exist_ok=True,token=token)
    readme=root/"README.md"
    if not readme.exists():
        readme.write_text("# "+root.name+"\n\nEksperymentalny model 321 AI trenowany od zera.\n",encoding="utf-8")
    api.upload_folder(repo_id=repo_id,repo_type="model",folder_path=str(root/"model"),
                      path_in_repo="model",commit_message="Upload trained 321 AI model")
    api.upload_file(path_or_fileobj=str(root/"config.json"),path_in_repo="config.json",
                    repo_id=repo_id,repo_type="model",commit_message="Upload training configuration")
    api.upload_file(path_or_fileobj=str(readme),path_in_repo="README.md",
                    repo_id=repo_id,repo_type="model",commit_message="Add model card")
    return f"https://huggingface.co/{repo_id}"

def download_dataset(repo_id: str, destination: str | Path, split: str="train",
                     max_examples: int=10000) -> tuple[Path,str]:
    if not 1 <= max_examples <= 1_000_000: raise ValueError("max_examples musi być w zakresie 1–1 000 000.")
    token=os.environ.get("HF_TOKEN") or None
    try:
        from huggingface_hub import HfApi
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Zainstaluj: pip install '321code-lang[huggingface]'") from exc
    info=HfApi(token=token).dataset_info(repo_id,token=token)
    card=info.card_data
    license_value=card.get("license","") if isinstance(card,dict) else getattr(card,"license","")
    license_id=str(license_value or "").lower()
    if license_id not in ALLOWED_DATASET_LICENSES:
        raise ValueError(f"Licencja datasetu „{license_id or 'niepodana'}” nie jest na liście automatycznie dozwolonych. Sprawdź ją ręcznie.")
    data=load_dataset(repo_id,split=split,streaming=True,token=token)
    target=Path(destination).expanduser().resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with target.open("w",encoding="utf-8") as stream:
        for row in data:
            clean={}
            for key,value in row.items():
                if isinstance(value,(str,int,float,bool)) or value is None:
                    clean[key]=value
            if clean:
                stream.write(json.dumps(clean,ensure_ascii=False)+"\n")
                count+=1
            if count>=max_examples: break
    if not count:
        target.unlink(missing_ok=True)
        raise ValueError("Dataset nie zawiera prostych pól tekstowych do eksportu.")
    return target,f"Pobrano {count:,} rekordów z {repo_id}; licencja: {license_id}."
