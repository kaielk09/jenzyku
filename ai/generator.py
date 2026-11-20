"""Research collector for 321 AI: multi-query, relevance and text quality scoring.
No paid services and no language model generation are used.
"""
from __future__ import annotations
import html
import re
import socket
import ipaddress
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from .understanding import understand_request

SEARCH_URL="https://html.duckduckgo.com/html/?q="
USER_AGENT="Mozilla/5.0 (compatible; 321code AI research/0.4)"

class _TextExtractor(HTMLParser):
 def __init__(self):
  super().__init__(); self.parts=[]; self.skip_depth=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style","noscript","svg","iframe","nav","footer","header","form","button"):
   self.skip_depth+=1
  elif tag in ("p","br","li","h1","h2","h3","h4","h5","article","section"):
   self.parts.append("\n")
 def handle_endtag(self,tag):
  if tag in ("script","style","noscript","svg","iframe","nav","footer","header","form","button") and self.skip_depth:
   self.skip_depth-=1
  elif tag in ("p","li","h1","h2","h3","h4","h5","article","section"):
   self.parts.append("\n")
 def handle_data(self,data):
  if not self.skip_depth: self.parts.append(data)

def _clean(raw):
 parser=_TextExtractor(); parser.feed(raw)
 text=html.unescape("".join(parser.parts))
 text=re.sub(r"[ \t]+"," ",text); text=re.sub(r"\n\s*\n+","\n",text)
 return text.strip()

def _safe_url(url):
 try:
  parsed=urllib.parse.urlparse(url)
  if parsed.scheme not in ("http","https") or not parsed.hostname: return False
  host=parsed.hostname.lower().rstrip(".")
  if host in {"localhost","localhost.localdomain"} or host.endswith(".local"): return False
  for item in socket.getaddrinfo(host,None):
   ip=ipaddress.ip_address(item[4][0])
   if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved: return False
  return True
 except Exception: return False

def search_web(query,max_results=6):
 if not query.strip(): return []
 request=urllib.request.Request(SEARCH_URL+urllib.parse.quote(query),headers={"User-Agent":USER_AGENT})
 with urllib.request.urlopen(request,timeout=12) as response:
  page=response.read(900_000).decode("utf-8",errors="replace")
 found=[]
 pattern=r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
 for match in re.finditer(pattern,page,re.I|re.S):
  url=html.unescape(match.group(1)); title=_clean(match.group(2))
  parsed=urllib.parse.urlparse(url)
  if parsed.hostname and "duckduckgo.com" in parsed.hostname and parsed.path.startswith("/l/"):
   url=urllib.parse.parse_qs(parsed.query).get("uddg",[""])[0]
  if url.startswith("//"): url="https:"+url
  if not _safe_url(url) or any(x["url"]==url for x in found): continue
  found.append({"title":title or "Wynik wyszukiwania","url":url,"query":query})
  if len(found)>=max_results: break
 return found

def _fetch(url,timeout=8):
 if not _safe_url(url): return ""
 request=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
 with urllib.request.urlopen(request,timeout=timeout) as response:
  if response.status!=200 or not _safe_url(response.geturl()): return ""
  return _clean(response.read(500_000).decode("utf-8",errors="replace"))

def _paragraphs(text):
 paragraphs=[]; seen=set()
 for item in re.split(r"\n+|(?<=[.!?])\s+",text):
  p=re.sub(r"\s+"," ",item).strip()
  if not 90<=len(p)<=1800: continue
  # Filter obvious boilerplate and low-value text.
  low=p.lower()
  if any(term in low for term in ("cookie policy","privacy policy","accept cookies","subscribe to our newsletter","skip to content")): continue
  if len(re.findall(r"[.!?]",p))<1: continue
  key=re.sub(r"[^a-z0-9ąćęłńóśźż]+","",low)
  if key and key not in seen: seen.add(key); paragraphs.append(p)
 return paragraphs

def _score(text,keywords,title=""):
 lower=text.lower(); title_l=title.lower()
 words=[w for w in set(keywords) if len(w)>=3]
 hits=sum(1 for w in words if w in lower)
 title_hits=sum(1 for w in words if w in title_l)
 length_score=min(len(text)/400,1.0)
 sentence_count=len(re.findall(r"[.!?]",text))
 structure=min(sentence_count/3,1.0)
 # A small quality signal for topic relevance, useful length, and sentence structure.
 return hits*3+title_hits*2+length_score+structure

def build_training_txt(prompt,destination,max_results=7,max_chars_per_page=2800):
 parsed=understand_request(prompt)
 candidates=[]
 for query in parsed["search_queries"]:
  try:
   batch=search_web(query,max_results=max_results)
   for item in batch:
    if not any(old["url"]==item["url"] for old in candidates): candidates.append(item)
  except Exception: continue
  if len(candidates)>=max_results*3: break
 if not candidates: raise RuntimeError("Wyszukiwarka nie zwróciła wyników. Spróbuj zmienić temat.")
 sources=[]; sections=[]; used_paragraphs=set(); inspected=0
 for source in candidates:
  if inspected>=max_results*3: break
  inspected+=1
  try: page=_fetch(source["url"])
  except Exception: page=""
  paragraphs=_paragraphs(page)
  if not paragraphs: continue
  ranked=sorted(paragraphs,key=lambda p:_score(p,parsed["keywords"],source["title"]),reverse=True)
  picked=[]
  for p in ranked:
   norm=re.sub(r"[^a-z0-9ąćęłńóśźż]+","",p.lower())
   if norm in used_paragraphs: continue
   # If keywords exist, reject very weak relevance instead of adding random filler.
   if parsed["keywords"] and _score(p,parsed["keywords"],source["title"])<1.2: continue
   used_paragraphs.add(norm); picked.append(p)
   if sum(map(len,picked))>=max_chars_per_page: break
  if not picked: continue
  excerpt="\n".join(picked)[:max_chars_per_page].strip()
  sources.append(source["url"])
  sections.append(
   f"ŹRÓDŁO: {source['title']}\nZAPYTANIE: {source['query']}\nURL: {source['url']}\n"
   f"OCENA DOPASOWANIA: {max(_score(p,parsed['keywords'],source['title']) for p in picked):.1f}\n\n{excerpt}"
  )
  if len(sections)>=max_results: break
 if not sections: raise RuntimeError("Znaleziono linki, ale nie udało się pobrać jakościowego tekstu pasującego do tematu.")
 header=(
  "321 AI | RESEARCH DATA v0.4\n"
  f"Polecenie: {parsed['original']}\nTemat: {parsed['topic']}\n"
  f"Klasa: {parsed['category']} | Typ materiału: {parsed['intent']}\n"
  f"Plan zapytań ({len(parsed['search_queries'])}):\n"
  + "\n".join("- "+q for q in parsed["search_queries"])+"\n"
  "To materiał źródłowy z internetu, nie tekst napisany przez model. Sprawdź poprawność, prawa i aktualność.\n"
  +("="*84)+"\n\n"
 )
 output=destination; output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(header+"\n\n".join(sections)+"\n",encoding="utf-8")
 return output.stat().st_size,sources
