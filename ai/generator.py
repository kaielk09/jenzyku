"""321 AI internet-assisted TXT dataset builder (experimental, no paid API)."""
from __future__ import annotations
import html
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SEARCH_URL = "https://html.duckduckgo.com/html/?q="

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript","svg"):
            self.skip+=1
        elif tag in ("p","br","div","li","h1","h2","h3","h4"):
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script","style","noscript","svg") and self.skip:
            self.skip-=1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def _clean(raw: str) -> str:
    parser=_TextExtractor()
    parser.feed(raw)
    text=html.unescape(" ".join(parser.parts))
    text=re.sub(r"\s+", " ", text)
    return text.strip()

def _fetch(url: str, timeout: int=10) -> str:
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme not in ("http","https") or not parsed.hostname:
        return ""
    if parsed.hostname.lower() in ("localhost","127.0.0.1","::1"):
        return ""
    req=urllib.request.Request(url, headers={"User-Agent":"321code AI dataset fetcher/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status!=200:
            return ""
        raw=response.read(800_000).decode("utf-8",errors="replace")
    return _clean(raw)

def search_web(query: str, max_results: int=4) -> list[dict]:
    """Search DuckDuckGo HTML results. This is a scraper and may break if DDG changes."""
    query=query.strip()
    if not query:
        return []
    url=SEARCH_URL+urllib.parse.quote(query)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; 321code/0.1)"})
    with urllib.request.urlopen(req,timeout=12) as response:
        page=response.read(900_000).decode("utf-8",errors="replace")
    results=[]
    for match in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',page,re.I|re.S):
        link=html.unescape(match.group(1))
        title=_clean(match.group(2))
        parsed=urllib.parse.urlparse(link)
        if "duckduckgo.com" in (parsed.hostname or "") and parsed.path.startswith("/l/"):
            params=urllib.parse.parse_qs(parsed.query)
            link=params.get("uddg",[""])[0]
        if link.startswith("//"):
            link="https:"+link
        if not link.startswith(("http://","https://")):
            continue
        results.append({"title":title,"url":link})
        if len(results)>=max_results:
            break
    return results

def build_training_txt(prompt: str, destination, max_results: int=4, max_chars_per_page: int=12_000) -> tuple[int,list[str]]:
    """Collect source excerpts into a TXT training draft; does not paraphrase like an LLM."""
    query=prompt.strip()
    if not query:
        raise ValueError("Wpisz temat, który AI ma wyszukać.")
    results=search_web(query,max_results=max_results)
    if not results:
        raise RuntimeError("Nie znaleziono wyników. Spróbuj zmienić opis.")
    sections=[f"TEMAT ZBIORU DANYCH: {query}\nŹródła z wyszukiwarki; tekst nie jest automatycznie parafrazowany przez model językowy.\n"]
    sources=[]
    for i,item in enumerate(results,1):
        try:
            text=_fetch(item["url"])
        except Exception:
            text=""
        if not text:
            continue
        excerpt=text[:max_chars_per_page]
        sections.append(f"\n\n=== ŹRÓDŁO {i}: {item['title']} ===\nURL: {item['url']}\n\n{excerpt}\n")
        sources.append(item["url"])
    if not sources:
        raise RuntimeError("Wyniki znaleziono, ale nie udało się pobrać treści stron.")
    dest=destination
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text("\n".join(sections),encoding="utf-8")
    return dest.stat().st_size,sources
