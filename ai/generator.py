"""Multi-query web research collector for 321 AI (no paid API; not an LLM)."""
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
USER_AGENT="Mozilla/5.0 (compatible; 321code AI research/0.3)"

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip_depth=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg","iframe","nav","footer","header"):
            self.skip_depth+=1
        elif tag in ("p","br","li","h1","h2","h3","h4","article","section"):
            self.parts.append("\n")
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg","iframe","nav","footer","header") and self.skip_depth:
            self.skip_depth-=1
        elif tag in ("p","li","h1","h2","h3","h4","article","section"):
            self.parts.append("\n")
    def handle_data(self,data):
        if not self.skip_depth: self.parts.append(data)

def _clean(raw):
    parser=_TextExtractor(); parser.feed(raw)
    text=html.unescape("".join(parser.parts))
    text=re.sub(r"[ \t]+"," ",text)
    text=re.sub(r"\n\s*\n+","\n",text)
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
    for m in re.finditer(pattern,page,re.I|re.S):
        url=html.unescape(m.group(1)); title=_clean(m.group(2))
        parsed=urllib.parse.urlparse(url)
        if parsed.hostname and "duckduckgo.com" in parsed.hostname and parsed.path.startswith("/l/"):
            url=urllib.parse.parse_qs(parsed.query).get("uddg",[""])[0]
        if url.startswith("//"): url="https:"+url
        if not _safe_url(url) or any(x["url"]==url for x in found): continue
        found.append({"title":title or "Search result","url":url,"query":query})
        if len(found)>=max_results: break
    return found

def _fetch(url,timeout=8):
    if not _safe_url(url): return ""
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if response.status!=200 or not _safe_url(response.geturl()): return ""
        raw=response.read(500_000).decode("utf-8",errors="replace")
    return _clean(raw)

def _paragraphs(text):
    result=[]; seen=set()
    for part in re.split(r"\n+|(?<=[.!?])\s+",text):
        part=re.sub(r"\s+"," ",part).strip()
        if not 80<=len(part)<=1600: continue
        key=re.sub(r"[^a-z0-9ąćęłńóśźż]+","",part.lower())
        if key and key not in seen:
            seen.add(key); result.append(part)
    return result

def _relevance(text,keywords):
    lower=text.lower()
    hits=sum(1 for kw in set(keywords) if len(kw)>=3 and kw in lower)
    return hits

def build_training_txt(prompt,destination,max_results=8,max_chars_per_page=3500):
    parsed=understand_request(prompt)
    results=[]
    for query in parsed["search_queries"]:
        try:
            for item in search_web(query,max_results=max_results):
                if not any(r["url"]==item["url"] for r in results):
                    results.append(item)
        except Exception:
            continue
        if len(results)>=max_results*2: break
    if not results:
        raise RuntimeError("Wyszukiwarka nie zwróciła wyników. Spróbuj krótszego lub dokładniejszego tematu.")
    sources=[]; blocks=[]; all_seen=set()
    for item in results:
        try: text=_fetch(item["url"])
        except Exception: text=""
        paras=_paragraphs(text)
        if not paras: continue
        # Prefer paragraphs matching the topic keywords; retain some neutral context too.
        ranked=sorted(paras,key=lambda p:_relevance(p,parsed["keywords"]),reverse=True)
        selected=[]
        for p in ranked:
            key=re.sub(r"[^a-z0-9ąćęłńóśźż]+","",p.lower())
            if key in all_seen: continue
            all_seen.add(key); selected.append(p)
            if sum(len(x) for x in selected)>=max_chars_per_page: break
        excerpt="\n".join(selected)[:max_chars_per_page].strip()
        if not excerpt: continue
        sources.append(item["url"])
        blocks.append(f"ŹRÓDŁO: {item['title']}\nZAPYTANIE: {item['query']}\nURL: {item['url']}\n\n{excerpt}")
        if len(blocks)>=8: break
    if not blocks:
        raise RuntimeError("Znaleziono linki, ale strony nie zawierają tekstu do zebrania.")
    head=(
      "321 AI | RESEARCH DATA TXT v0.3\n"
      f"Polecenie użytkownika: {parsed['original']}\n"
      f"Temat: {parsed['topic']}\n"
      f"Klasyfikacja: {parsed['category']} | Rodzaj: {parsed['intent']}\n"
      "Wyniki zebrano z kilku zapytań i stron. To NIE jest odpowiedź wygenerowana przez model językowy; "
      "fragmenty są źródłowe, sprawdź dokładność, licencje i aktualność.\n"
      +("="*78)+"\n\n"
    )
    out=destination; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(head+"\n\n".join(blocks)+"\n",encoding="utf-8")
    return out.stat().st_size,sources
