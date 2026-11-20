"""Request analysis and query planning for the 321 AI research collector.
Heuristic only: no neural model or LLM is used.
"""
from __future__ import annotations
import re

STOP={
 "zrob","zrób","stworz","stwórz","napisz","wygeneruj","generuj","znajdz","znajdź",
 "wyszukaj","dowiedz","sie","się","o","na","do","dla","i","oraz","jak","co","czy",
 "opis","opisz","mi","prosze","proszę","chce","chcę","potrzebuje","potrzebuję",
 "plik","txt","tekst","dane","trening","dataset","zbior","zbiór","informacje","info",
 "podstawowe","przykłady","przyklady","wyjaśnienia","wyjasnienia","fakty","poradnik"
}
TOPIC_FACETS=["definicja i podstawy","jak działa mechanizm","przykłady zastosowań","najważniejsze cechy i fakty","częste błędy i problemy"]
ALIASES={
 "programowanie":["programowanie podstawy","programowanie przykłady","programowanie dobre praktyki"],
 "Minecraft/modowanie":["Minecraft mechaniki","Minecraft poradniki","Minecraft modding dokumentacja"],
 "historia":["historia chronologia","historia przyczyny i skutki","historia ważne postacie"],
 "matematyka":["matematyka wyjaśnienia","matematyka zadania przykłady"],
 "biologia":["biologia pojęcia","biologia procesy","biologia przykłady"],
 "fizyka":["fizyka prawa","fizyka zjawiska","fizyka zastosowania"],
 "chemia":["chemia pojęcia","chemia reakcje","chemia przykłady"],
 "geografia":["geografia fakty","geografia procesy","geografia przykłady"],
}
def _words(text):
 return [w for w in re.findall(r"[a-ząćęłńóśźż0-9_+-]{2,}",text.lower()) if w not in STOP]
def understand_request(prompt):
 raw=prompt.strip()
 if not raw: raise ValueError("Polecenie jest puste.")
 p=raw.lower(); tokens=_words(raw)
 topic=" ".join(tokens) or raw
 category="ogólny"
 rules=[
  (r"python|javascript|java|program|kod|skrypt|api|html|css|sql|linux|git|c\+\+", "programowanie"),
  (r"minecraft|mod|modowanie|redstone","Minecraft/modowanie"),
  (r"histori|wojn|król|królow|państw|bitw","historia"),
  (r"matemat|algebra|geometr|równan|ułam|procent","matematyka"),
  (r"biolog|organizm|komór|ekosystem|gen","biologia"),
  (r"fizyk|energi|ruch|sił|elektry|magnet","fizyka"),
  (r"chem|reakcj|pierwiast|cząstec","chemia"),
  (r"geograf|klimat|kontynent|państw","geografia"),
 ]
 for pattern,label in rules:
  if re.search(pattern,p): category=label; break
 intent="general_reference"
 if re.search(r"txt|tekst|dane|zbior|dataset|trening|train",p): intent="training_text"
 elif re.search(r"kod|program|python|javascript|script|skrypt|przykład kod",p): intent="code_reference"
 elif re.search(r"wyjaś|wytłum|opis|definic|czym jest|co to",p): intent="explanation_reference"
 queries=[raw]
 if topic and topic.lower()!=raw.lower(): queries.append(topic)
 # Category-oriented, multi-angle queries help diversify search results.
 queries.extend(ALIASES.get(category,[]))
 if topic and category!="ogólny":
  queries.extend([f"{topic} {facet}" for facet in TOPIC_FACETS[:3]])
 queries=list(dict.fromkeys(q.strip() for q in queries if q.strip()))[:7]
 return {
  "original":raw,"topic":topic,"intent":intent,"category":category,
  "search_queries":queries,"output_format":"TXT","needs_web":True,
  "keywords":tokens[:24],"facets":TOPIC_FACETS,
  "note":"Heuristic query planner; not an LLM."
}
