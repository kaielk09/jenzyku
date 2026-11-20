"""Web-assisted dataset builder for 321 AI (rule-based, not an LLM)."""
from __future__ import annotations
import html
import re
import socket
import ipaddress
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from .understanding import understand_request

SEARCH_URL = "https://html.duckduckgo.com/html/?q="

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.skip_depth=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript","svg","iframe"):
            self.skip_depth+=1
        elif tag in ("p","br","div","li","h1","h2","h3","h4","article","section"):
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script","style","noscript","svg","iframe") and self.skip_depth:
            self.skip_depth-=1
        elif tag in ("p","div","li","h1","h2","h3","h4","article","section"):
            self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)

def _clean(raw: str) -> str:
    parser=_TextExtractor()
    parser.feed(raw)
    text=html.unescape("".join(parser.parts))
    text=re.sub(r"[ \t]+"," ",text)
    text=re.sub(r"\n\s*\n+", "\n",text)
    return text.strip()

def _safe_url(url: str) -> bool:
    try:
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme not in ("http","https") or not parsed.hostname:
            return False
        host=parsed.hostname.lower().rstrip(".")
        if host in {"localhost","localhost.localdomain"} or host.endswith(".local"):
            return False
        addresses=socket.getaddrinfo(host,None)
        for item in addresses:
            ip=ipaddress.ip_address(item[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except Exception:
        return False

def _fetch(url: str, timeout: int=9) -> str:
    if not _safe_url(url):
        return ""
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; 321code AI dataset/0.2)"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        final_url=response.geturl()
        if not _safe_url(final_url) or response.status!=200:
            return ""
        raw=response.read(600_000).decode("utf-8",errors="replace")
    return _clean(raw)

def search_web(query: str, max_results: int=5) -> list[dict]:
    query=query.strip()
    if not query:
        return []
    req=urllib.request.Request(SEARCH_URL+urllib.parse.quote(query),headers={"User-Agent":"Mozilla/5.0 (compatible; 321code/0.2)"})
    with urllib.request.urlopen(req,timeout=12) as response:
        page=response.read(900_000).decode("utf-8",errors="replace")
    results=[]
    # Parse DDG result anchors with a tolerant pattern.
    for match in re.finditer(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',page,re.I|re.S):
        link=html.unescape(match.group(1))
        title=_clean(match.group(2))
        parsed=urllib.parse.urlparse(link)
        if parsed.hostname and "duckduckgo.com" in parsed.hostname and parsed.path.startswith("/l/"):
            link=urllib.parse.parse_qs(parsed.query).get("uddg",[""])[0]
        if link.startswith("//"):
            link="https:"+link
        if not _safe_url(link):
            continue
        if any(r["url"]==link for r in results):
            continue
        results.append({"title":title or "Wynik wyszukiwania","url":link})
        if len(results)>=max_results:
            break
    return results

def _dedupe_paragraphs(text: str) -> list[str]:
    paragraphs=[]
    seen=set()
    for p in re.split(r"\n+|(?<=[.!?])\s+",text):
        p=re.sub(r"\s+"," ",p).strip()
        if len(p)<70 or len(p)>1500:
            continue
        key=re.sub(r"[^a-z0-9ąćęłńóśźż]+","",p.lower())
        if key and key not in seen:
            seen.add(key)
            paragraphs.append(p)
    return paragraphs

def build_training_txt(prompt: str, destination, max_results: int=5, max_chars_per_page: int=2_000) -> tuple[int,list[str]]:
    understood=understand_request(prompt)
    results=search_web(understood["search_query"],max_results=max_results)
    if not results:
        raise RuntimeError("Nie znaleziono wyników wyszukiwania. Zmień opis albo spróbuj później.")
    sources=[]
    blocks=[]
    for item in results:
        try:
            page_text=_fetch(item["url"])
        except Exception:
            page_text=""
        paragraphs=_dedupe_paragraphs(page_text)
        if not paragraphs:
            continue
        excerpt="\n".join(paragraphs)[:max_chars_per_page].strip()
        if not excerpt:
            continue
        sources.append(item["url"])
        blocks.append(f"ŹRÓDŁO: {item['title']}\nURL: {item['url']}\n\n{excerpt}")
    if not blocks:
        raise RuntimeError("Wyszukano strony, ale nie udało się pobrać sensownego tekstu.")
    header=(
        "321 AI — DRAFT DANYCH TRENINGOWYCH\n"
        f"Polecenie: {understood['original']}\n"
        f"Rozpoznany obszar: {understood['category']}\n"
        f"Typ: {understood['intent']}\n"
        "Uwaga: to uporządkowane fragmenty pobrane ze źródeł; generator nie parafrazuje ich przez model językowy. "
        "Sprawdź prawa/licencje i poprawność przed użyciem do treningu.\n"
        + ("-"*72)+"\n"
    )
    output=header+"\n\n".join(blocks)+"\n"
    dest=destination
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(output,encoding="utf-8")
    return dest.stat().st_size,sources
