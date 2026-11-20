"""Auto-build an image dataset from Wikimedia Commons with license metadata.
Uses Commons' public API for discovery; no pretrained model or image-generation API.
"""
from __future__ import annotations
import argparse, json, random, re, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PIL import Image, ImageOps
import io

API="https://commons.wikimedia.org/w/api.php"
UA="321code-image-dataset/1.0 (educational local trainer)"
CATEGORIES={
 "random":"Category:Featured pictures",
 "nature":"Category:Natural phenomena",
 "landscapes":"Category:Landscape photographs",
 "animals":"Category:Animals",
 "architecture":"Category:Architecture",
 "objects":"Category:Objects",
 "space":"Category:Astronomical objects",
 "plants":"Category:Plants",
}

def api(params):
 params={"format":"json","origin":"*","maxlag":5,**params}
 req=Request(API+"?"+urlencode(params),headers={"User-Agent":UA})
 with urlopen(req,timeout=25) as r: return json.loads(r.read().decode("utf-8"))

def list_files(category,limit):
 # Commons categorymember results, randomize a broad sample
 data=api({"action":"query","list":"categorymembers","cmtitle":category,"cmtype":"file","cmlimit":min(limit*3,100),"cmnamespace":6})
 files=data.get("query",{}).get("categorymembers",[])
 random.shuffle(files)
 return files[:limit]

def metadata(pageid):
 data=api({"action":"query","pageids":pageid,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":512})
 page=next(iter(data.get("query",{}).get("pages",{}).values()),{})
 ii=(page.get("imageinfo") or [{}])[0]
 ext=ii.get("extmetadata",{})
 license_name=ext.get("LicenseShortName",{}).get("value","")
 license_url=ext.get("LicenseUrl",{}).get("value","")
 # Only freely licensed / public-domain items; refuse unclear license status.
 if not any(x in license_name.lower() for x in ("cc","public domain","pd")):
  return None
 return {"title":page.get("title",""),"url":ii.get("thumburl") or ii.get("url",""),
         "source_url":ii.get("descriptionurl",""),"license":license_name,"license_url":license_url,
         "author":ext.get("Artist",{}).get("value","")}

def download(url):
 req=Request(url,headers={"User-Agent":UA})
 with urlopen(req,timeout=30) as r: data=r.read(8*1024*1024+1)
 if len(data)>8*1024*1024: return None
 try:
  im=Image.open(io.BytesIO(data)); im.verify()
  im=Image.open(io.BytesIO(data)).convert("RGB")
  im=ImageOps.fit(im,(256,256),method=Image.Resampling.LANCZOS)
  buf=io.BytesIO(); im.save(buf,format="JPEG",quality=92,optimize=True)
  return buf.getvalue()
 except Exception: return None

def collect(category, count, out):
 if category not in CATEGORIES: raise ValueError("Nieznana kategoria kolekcji.")
 out=Path(out); out.mkdir(parents=True,exist_ok=True)
 records=[]; skipped=0
 candidates=list_files(CATEGORIES[category],count)
 for item in candidates:
  if len(records)>=count: break
  try:
   meta=metadata(str(item["pageid"]))
   if not meta: skipped+=1; continue
   data=download(meta["url"])
   if not data: skipped+=1; continue
   filename=f"commons_{item['pageid']}.jpg"
   (out/filename).write_bytes(data)
   records.append({"file":filename,**meta,"dataset":"Wikimedia Commons","downloaded_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
   print(f"[{len(records)}/{count}] {filename} | {meta['license']}",flush=True)
  except Exception as e:
   skipped+=1; print("Skip:",str(e)[:160],flush=True)
 manifest=out/"dataset_manifest.json"
 manifest.write_text(json.dumps({"source":"Wikimedia Commons","category":category,"collected":len(records),"skipped":skipped,"items":records},indent=2,ensure_ascii=False),encoding="utf-8")
 print(f"Dataset gotowy: {len(records)} obrazów; pominięto {skipped}. Manifest licencji: {manifest}")
 return len(records)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--category",choices=CATEGORIES,required=True)
 p.add_argument("--count",type=int,default=100)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 if not 8<=a.count<=1000: raise SystemExit("Limit kolekcji: 8–1000 obrazów.")
 collect(a.category,a.count,a.out)
if __name__=="__main__": main()
