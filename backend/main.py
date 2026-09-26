import os
import re
import asyncio
import types

# mega.py 1.0.8 depends on tenacity 5.x, which still references
# asyncio.coroutine. Python 3.11 removed that alias, so restore the
# compatible alias before importing mega.py.
if not hasattr(asyncio, "coroutine"):
    asyncio.coroutine = types.coroutine

import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mega import Mega
from starlette.background import BackgroundTask

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
    global _mega
    if not MEGA_EMAIL or not MEGA_PASSWORD:
        raise HTTPException(500, "Mega credentials are not configured")
    if _mega is None:
        try:
            _mega = Mega().login(MEGA_EMAIL, MEGA_PASSWORD)
        except Exception as exc:
            raise HTTPException(502, f"Mega login failed: {exc}")
    return _mega

_mega = None


def safe_name(title: str, artist: str, source_url: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", f"{artist}-{title}").strip("_")[:100]
    digest = __import__("hashlib").sha256(source_url.encode()).hexdigest()[:16]
    return f"{base or 'song'}-{digest}.mp3"


def find_cached_song(mega, folder, source_url: str):
    digest = __import__("hashlib").sha256(source_url.encode()).hexdigest()[:16]
    files = mega.get_files()
    for _, node in files.items():
        # mega.py stores the decrypted filename under node["a"]["n"],
        # not node["name"].
        node_name = (node.get("a") or {}).get("n") or node.get("name") or ""
        if node.get("t") == 0 and node_name.endswith(f"-{digest}.mp3"):
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

    # mega.py has two different return shapes here:
    # find() returns a node/list, while create_folder() returns a dict
    # like {"RomaMusic": "<node-id>"}. Normalize both to one node id.
    folder = mega.find(MEGA_FOLDER)
    if folder:
        if isinstance(folder, list):
            folder_id = folder[0] if folder else None
        elif isinstance(folder, tuple):
            folder_id = folder[0] if folder else None
        else:
            folder_id = folder
    else:
        created = mega.create_folder(MEGA_FOLDER)
        folder_id = created.get(MEGA_FOLDER) if isinstance(created, dict) else created

    if not folder_id:
        raise HTTPException(502, "Mega folder could not be created or found")

    cached = find_cached_song(mega, folder_id, url)
    if cached:
        try:
            return {
                "stream_url": f"/api/stream?source_url={quote(url, safe='')}",
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

        # mega.py's upload() is synchronous, so run it off the FastAPI
        # event loop. The destination must be the actual Mega node id.
        uploaded = await asyncio.to_thread(
            mega.upload,
            str(temp_path),
            folder_id,
        )

        if not uploaded:
            raise RuntimeError("Mega upload returned no file node")

        return {
            "stream_url": f"/api/stream?source_url={quote(url, safe='')}",
            "cached": False,
            "title": title,
            "artist": artist,
            "thumbnail": thumbnail,
        }
    except Exception as exc:
        raise HTTPException(502, f"Mega storage failed: {exc}")
    finally:
        temp_path.unlink(missing_ok=True)


@app.get("/api/stream")
async def stream(source_url: str):
    """Serve a cached Mega file as actual audio bytes."""
    if not source_url.strip():
        raise HTTPException(400, "Source URL is required")

    mega = mega_client()
    cached = find_cached_song(mega, None, source_url)
    if not cached:
        raise HTTPException(404, "Cached song not found")

    filename = cached.get("name") or "song.mp3"
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename)
    target = TEMP_DIR / safe_filename

    try:
        # Download the private Mega node directly. Creating a public
        # Mega share link is unnecessary and can fail for account files.
        # mega.py expects the normal find()/node tuple shape here.
        await asyncio.to_thread(
            mega.download,
            ("cached", cached),
            str(TEMP_DIR),
            safe_filename,
        )
        if not target.exists() or target.stat().st_size == 0:
            raise RuntimeError("Mega download produced an empty audio file")

        # Keep the response inline so the HTML audio element can consume it
        # as media instead of treating it as a forced download.
        return FileResponse(
            target,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="{safe_filename}"',
                "Cache-Control": "public, max-age=3600",
            },
            background=BackgroundTask(lambda: target.unlink(missing_ok=True)),
        )
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(502, f"Mega playback failed: {exc}")
