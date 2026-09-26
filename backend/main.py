from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from cache import connect

app = FastAPI(title="Roma Music API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

SEARCH_APIS = [
    "https://jerrycoder.oggyapi.workers.dev/search/spotify?q=",
    "https://api.nexray.eu.cc/search/spotify?q=",
    "https://zellrayy.com/search/spotify?q=",
]
DOWNLOAD_APIS = [
    "https://jerrycoder.oggyapi.workers.dev/down/spotify?url=",
    "https://api.nexray.eu.cc/downloader/spotify?url=",
    "https://valora-api.vercel.app/download/spotify?url=",
]

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

@app.get("/")
async def root():
    return FileResponse(FRONTEND / "index.html")

@app.get("/api/search")
async def search(q: str):
    if not q.strip():
        return {"result": []}
    async with httpx.AsyncClient(timeout=10) as client:
        for provider in SEARCH_APIS:
            try:
                r = await client.get(provider + q)
                if r.status_code == 200 and r.json():
                    return r.json()
            except Exception:
                continue
    raise HTTPException(502, "Search providers unavailable")

@app.get("/api/download")
async def download(url: str, title: str = "", artist: str = "", thumbnail: str = ""):
    if not url.strip():
        raise HTTPException(400, "Song URL is required")

    with connect() as db:
        cached = db.execute(
            "SELECT audio_url FROM songs WHERE source_url=? AND audio_url IS NOT NULL",
            (url,)
        ).fetchone()
        if cached:
            db.execute(
                "UPDATE songs SET play_count=play_count+1,last_played_at=CURRENT_TIMESTAMP WHERE source_url=?",
                (url,)
            )
            song = db.execute("SELECT id FROM songs WHERE source_url=?", (url,)).fetchone()
            if song:
                db.execute("INSERT INTO play_history(song_id) VALUES(?)", (song["id"],))
            db.commit()
            return {"download_url": cached["audio_url"], "cached": True}

    async with httpx.AsyncClient(timeout=15) as client:
        for provider in DOWNLOAD_APIS:
            try:
                r = await client.get(provider + url)
                if r.status_code != 200:
                    continue
                data = r.json()
                audio = data.get("download_link") or data.get("download_url") or (data.get("result") or {}).get("url") or data.get("url")
                if not audio:
                    continue
                with connect() as db:
                    db.execute(
                        """INSERT INTO songs(title,artist,thumbnail,source_url,audio_url,play_count,last_played_at)
                           VALUES(?,?,?,?,?,1,CURRENT_TIMESTAMP)
                           ON CONFLICT(source_url) DO UPDATE SET
                           title=excluded.title,artist=excluded.artist,thumbnail=excluded.thumbnail,
                           audio_url=excluded.audio_url,play_count=songs.play_count+1,last_played_at=CURRENT_TIMESTAMP""",
                        (title or "Unknown song", artist, thumbnail, url, audio)
                    )
                    song = db.execute("SELECT id FROM songs WHERE source_url=?", (url,)).fetchone()
                    if song:
                        db.execute("INSERT INTO play_history(song_id) VALUES(?)", (song["id"],))
                    db.commit()
                return {**data, "cached": False}
            except Exception:
                continue
    raise HTTPException(502, "Download providers unavailable")
