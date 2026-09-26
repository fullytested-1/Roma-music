import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from mega import Mega

app = FastAPI(title="Roma Music API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
TEMP_DIR = ROOT / "tmp"
TEMP_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

MEGA_EMAIL = os.getenv("MEGA_EMAIL", "")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD", "")
MEGA_FOLDER = os.getenv("MEGA_FOLDER", "RomaMusic")


def mega_client():
    if not MEGA_EMAIL or not MEGA_PASSWORD:
        raise HTTPException(500, "Mega credentials are not configured")
    return Mega().login(MEGA_EMAIL, MEGA_PASSWORD)


def safe_name(title: str, artist: str, source_url: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", f"{artist}-{title}").strip("_")[:100]
    digest = __import__("hashlib").sha256(source_url.encode()).hexdigest()[:16]
    return f"{base or 'song'}-{digest}.mp3"


def find_cached_song(mega, folder, source_url: str):
    digest = __import__("hashlib").sha256(source_url.encode()).hexdigest()[:16]
    files = mega.get_files()
    for _, node in files.items():
        if node.get("t") == 0 and node.get("name", "").endswith(f"-{digest}.mp3"):
            return node
    return None


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
                r = await client.get(provider + quote(q, safe=""))
                if r.status_code == 200 and r.json():
                    return r.json()
            except Exception:
                continue
    raise HTTPException(502, "Search providers unavailable")


async def provider_audio_url(url: str):
    async with httpx.AsyncClient(timeout=20) as client:
        for provider in DOWNLOAD_APIS:
            try:
                r = await client.get(provider + quote(url, safe=""))
                if r.status_code != 200:
                    continue
                data = r.json()
                audio = (
                    data.get("download_link")
                    or data.get("download_url")
                    or (data.get("result") or {}).get("url")
                    or data.get("url")
                )
                if audio:
                    return audio
            except Exception:
                continue
    return None


@app.get("/api/download")
async def download(
    url: str,
    title: str = "",
    artist: str = "",
    thumbnail: str = "",
):
    if not url.strip():
        raise HTTPException(400, "Song URL is required")

    mega = mega_client()
    folder = mega.find(MEGA_FOLDER)
    if not folder:
        folder = mega.create_folder(MEGA_FOLDER)

    cached = find_cached_song(mega, folder, url)
    if cached:
        try:
            return {
                "download_url": mega.get_upload_link(cached),
                "cached": True,
                "title": title,
                "artist": artist,
                "thumbnail": thumbnail,
            }
        except Exception:
            pass

    audio_url = await provider_audio_url(url)
    if not audio_url:
        raise HTTPException(502, "Download providers unavailable")

    filename = safe_name(title or "Unknown song", artist or "Unknown artist", url)
    temp_path = TEMP_DIR / filename

    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            async with client.stream("GET", audio_url) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as out:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        out.write(chunk)

        uploaded = mega.upload(str(temp_path), folder[0] if isinstance(folder, list) else folder)
        link = mega.get_upload_link(uploaded)
        return {
            "download_url": link,
            "cached": False,
            "title": title,
            "artist": artist,
            "thumbnail": thumbnail,
        }
    except Exception as exc:
        raise HTTPException(502, f"Mega storage failed: {exc}")
    finally:
        temp_path.unlink(missing_ok=True)
