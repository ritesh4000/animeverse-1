import json, os, re, time
from contextlib import asynccontextmanager
from urllib.request import Request, urlopen
import mysql.connector
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

VEC=None
MATRIX=None
ANIME=[]
INDEX={}
POSTER_CACHE={}
ANILIST_URL="https://graphql.anilist.co"

def db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST","db"),
        port=int(os.getenv("MYSQL_PORT","3306")),
        database=os.getenv("MYSQL_DATABASE","animeverse"),
        user=os.getenv("MYSQL_USER","animeverse"),
        password=os.getenv("MYSQL_PASSWORD","")
    )

def fetch(sql, params=()):
    c=db(); cur=c.cursor(dictionary=True)
    cur.execute(sql, params); rows=cur.fetchall()
    cur.close(); c.close()
    return rows

def anime_filters(q="",genre="",anime_type="",min_score=0):
    where=" WHERE 1=1"
    params=[]
    if q:
        where+=" AND (name LIKE %s OR genres LIKE %s OR studios LIKE %s)"
        value="%"+q+"%"; params += [value,value,value]
    if genre:
        where+=" AND genres LIKE %s"; params.append("%"+genre+"%")
    if anime_type:
        where+=" AND type=%s"; params.append(anime_type)
    where+=" AND (score IS NULL OR score >= %s)"; params.append(float(min_score))
    return where,params

def fetch_posters(titles):
    missing=list(dict.fromkeys(title for title in titles if title and title not in POSTER_CACHE))
    if missing:
        definitions=", ".join(f"$q{i}: String" for i in range(len(missing)))
        fields=" ".join(
            f"m{i}: Page(page: 1, perPage: 1) "
            f"{{ media(search: $q{i}, type: ANIME, isAdult: false) "
            "{ coverImage { large color } } }"
            for i in range(len(missing))
        )
        request=Request(
            ANILIST_URL,
            data=json.dumps({
                "query":f"query ({definitions}) {{ {fields} }}",
                "variables":{f"q{i}":title for i,title in enumerate(missing)}
            }).encode("utf-8"),
            headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"Animeverse/1.0"},
            method="POST"
        )
        try:
            with urlopen(request,timeout=10) as response:
                data=json.loads(response.read().decode("utf-8")).get("data") or {}
            for i,title in enumerate(missing):
                media=(data.get(f"m{i}") or {}).get("media") or []
                cover=(media[0] if media else {}).get("coverImage") or {}
                image=cover.get("large")
                color=cover.get("color")
                POSTER_CACHE[title]={
                    "image_url":image if isinstance(image,str) and image.startswith("https://") else None,
                    "image_color":color if isinstance(color,str) and re.fullmatch(r"#[0-9a-fA-F]{6}",color) else "#312e81"
                }
        except Exception:
            pass
    return {title:POSTER_CACHE.get(title,{"image_url":None,"image_color":"#312e81"}) for title in titles}

def train_model():
    global VEC,MATRIX,ANIME,INDEX
    for _ in range(30):
        try:
            ANIME=fetch("""SELECT id,name,score,popularity,genres,studios,type,year,episodes,
                                  themes,demographic,members,synopsis,features FROM anime
                           ORDER BY id""")
            break
        except Exception:
            time.sleep(2)
    if not ANIME:
        raise RuntimeError("MySQL is reachable but anime table is empty.")
    texts=[x.get("features") or "" for x in ANIME]
    VEC=TfidfVectorizer(stop_words="english",ngram_range=(1,2),min_df=1)
    MATRIX=VEC.fit_transform(texts)
    INDEX={int(x["id"]):i for i,x in enumerate(ANIME)}

@asynccontextmanager
async def lifespan(app):
    train_model()
    yield

app=FastAPI(title="ANIMEVERSE API",version="1.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
app.mount("/static",StaticFiles(directory="static"),name="static")

@app.get("/")
def home(): return FileResponse("static/index.html")

@app.get("/api/health")
def health():
    try:
        n=fetch("SELECT COUNT(*) AS n FROM anime")[0]["n"]
        return {"status":"ok","database":"mysql","anime":n,"ml":"tfidf_ready" if MATRIX is not None else "not_ready"}
    except Exception as e:
        return {"status":"error","detail":str(e)}

@app.get("/api/stats")
def stats():
    summary=fetch("""SELECT COUNT(*) total_anime,
                            ROUND(AVG(score),2) avg_score,
                            MIN(year) min_year, MAX(year) max_year
                     FROM anime""")[0]
    summary["studios"]=len({
        studio.strip()
        for anime in ANIME
        for studio in (anime.get("studios") or "").split(",")
        if studio.strip()
    })
    summary["genres"]=len({
        genre.strip()
        for anime in ANIME
        for genre in (anime.get("genres") or "").split(",")
        if genre.strip()
    })
    return summary

@app.get("/api/anime")
def anime(q:str="",genre:str="",type:str="",min_score:float=0,limit:int=24,offset:int=0):
    limit=max(1,min(limit,100)); offset=max(0,offset)
    where,p=anime_filters(q,genre,type,min_score)
    sql="""SELECT id,name,score,popularity,genres,studios,type,year,episodes
           FROM anime"""+where
    sql+=" ORDER BY COALESCE(score,0) DESC, COALESCE(popularity,2147483647) ASC LIMIT %s OFFSET %s"
    p += [limit,offset]
    return fetch(sql,p)

@app.get("/api/library")
def library(q:str="",genre:str="",type:str="",min_score:float=0,sort:str="rating",limit:int=18,offset:int=0):
    limit=max(1,min(limit,30)); offset=max(0,offset)
    where,params=anime_filters(q,genre,type,min_score)
    ordering={
        "rating":"COALESCE(score,0) DESC, COALESCE(popularity,2147483647) ASC",
        "popular":"COALESCE(popularity,2147483647) ASC, COALESCE(score,0) DESC",
        "newest":"COALESCE(year,0) DESC, COALESCE(score,0) DESC",
        "title":"name ASC"
    }.get(sort,"COALESCE(score,0) DESC, COALESCE(popularity,2147483647) ASC")
    total=fetch("SELECT COUNT(*) total FROM anime"+where,params)[0]["total"]
    items=fetch("""SELECT id,name,score,popularity,genres,studios,type,year,episodes
                   FROM anime"""+where+f" ORDER BY {ordering} LIMIT %s OFFSET %s",params+[limit,offset])
    posters=fetch_posters([item["name"] for item in items])
    for item in items:
        item.update(posters[item["name"]])
    return {"items":items,"total":total,"limit":limit,"offset":offset}

@app.get("/api/anime/{anime_id}")
def detail(anime_id:int):
    r=fetch("SELECT * FROM anime WHERE id=%s",(anime_id,))
    if not r: raise HTTPException(404,"Anime not found")
    return r[0]

@app.get("/api/recommendations/{anime_id}")
def recommendations(anime_id:int,limit:int=10):
    if anime_id not in INDEX: raise HTTPException(404,"Anime not found")
    i=INDEX[anime_id]
    sims=cosine_similarity(MATRIX[i],MATRIX).ravel()
    order=sims.argsort()[::-1]
    out=[]
    for j in order:
        if j==i: continue
        x=dict(ANIME[j]); x["similarity"]=round(float(sims[j]),4)
        out.append(x)
        if len(out)>=min(limit,30): break
    return out

@app.get("/api/hidden-gems")
def gems(limit:int=12):
    rows=fetch("""SELECT id,name,score,popularity,genres,studios,type,year
                  FROM anime
                  WHERE score IS NOT NULL AND popularity IS NOT NULL AND score>=7.5
                  ORDER BY score DESC, popularity DESC
                  LIMIT %s""",(min(limit,50),))
    return rows

@app.get("/api/meta")
def meta():
    genres=fetch("SELECT genres FROM anime WHERE genres<>''")
    types=fetch("SELECT DISTINCT type FROM anime WHERE type<>'' ORDER BY type")
    gs=set()
    for r in genres:
        for g in (r["genres"] or "").split(","):
            if g.strip(): gs.add(g.strip())
    return {"genres":sorted(gs),"types":[x["type"] for x in types]}
