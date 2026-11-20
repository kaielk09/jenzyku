"""Rule-based request understanding for 321 AI web research.
This module creates a search plan; it is not a trained language model.
"""
from __future__ import annotations
import re

STOP = {
 "zrob","zrób","stworz","stwórz","napisz","wygeneruj","generuj","znajdz","znajdź",
 "wyszukaj","dowiedz","sie","się","o","na","do","dla","i","oraz","jak","co","czy",
 "opis","opisz","mi","prosze","proszę","chce","chcę","potrzebuje","potrzebuję",
 "plik","txt","tekst","dane","trening","dataset","zbior","zbiór","informacje","info"
}
ALIASES = {
 "python": ["Python język programowania podstawy","Python przykłady kod"],
 "minecraft": ["Minecraft poradnik","Minecraft mechaniki i przykłady"],
 "historia": ["historia fakty i wydarzenia","historia chronologia"],
 "matematyka": ["matematyka definicje przykłady","matematyka wyjaśnienia"],
 "biologia": ["biologia fakty i wyjaśnienia","biologia przykłady"],
 "fizyka": ["fizyka pojęcia przykłady","fizyka wyjaśnienia"],
}

def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-ząćęłńóśźż0-9_+-]{2,}",text.lower()) if w not in STOP]

def understand_request(prompt: str) -> dict:
    raw=prompt.strip()
    if not raw:
        raise ValueError("Polecenie jest puste.")
    p=raw.lower()
    tokens=_words(raw)
    topic=" ".join(tokens) or raw
    category="ogólny"
    rules=[
      (r"python|javascript|java|program|kod|skrypt|api|html|css|sql|linux|git", "programowanie"),
      (r"minecraft|mod|modowanie|redstone", "Minecraft/modowanie"),
      (r"histori|wojn|król|królow|państw|bitw", "historia"),
      (r"matemat|algebra|geometr|równan|ułam|procent", "matematyka"),
      (r"biolog|organizm|komór|ekosystem|gen", "biologia"),
      (r"fizyk|energi|ruch|sił|elektry|magnet", "fizyka"),
      (r"chem|reakcj|pierwiast|cząstec", "chemia"),
      (r"geograf|klimat|kontynent|państw", "geografia"),
    ]
    for pattern,label in rules:
        if re.search(pattern,p):
            category=label
            break
    # Detect the user's expected material type.
    intent="general_reference"
    if re.search(r"txt|tekst|dane|zbior|dataset|trening|train",p):
        intent="training_text"
    elif re.search(r"kod|program|python|javascript|script|skrypt|przykład kod",p):
        intent="code_reference"
    elif re.search(r"wyjaś|wytłum|opis|definic|czym jest|co to",p):
        intent="explanation_reference"
    # Multiple, differently phrased searches improve coverage; avoid losing the main topic.
    variants=[raw]
    cleaned=topic.strip()
    if cleaned and cleaned.lower()!=raw.lower():
        variants.append(cleaned)
    if category in ALIASES:
        variants.extend(ALIASES[category])
    variants=list(dict.fromkeys(q.strip() for q in variants if q.strip()))[:4]
    return {
      "original":raw,"topic":topic,"intent":intent,"category":category,
      "search_queries":variants,"output_format":"TXT","needs_web":True,
      "keywords":tokens[:20],
      "note":"Rule-based search planner, not an LLM."
    }
