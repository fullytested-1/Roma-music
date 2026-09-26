import os
import re
import asyncio
import hashlib
import shutil
import time
from pathlib import Path
from urllib.parse import quote

import cloudinary
import cloudinary.api
import cloudinary.uploader
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "").strip()
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "").strip()
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "RomaMusic").strip().strip("/")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )


def require_cloudinary():
    if not all(
        [CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]
    ):
        raise HTTPException(
            500,
            "Cloudinary credentials are not configured",
        )


def public_id_for(source_url: str) -> str:
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    return f"{CLOUDINARY_FOLDER}/{digest}" if CLOUDINARY_FOLDER else digest


def safe_name(title: str, artist: str, source_url: str) -> str:
    base = re.sub(
        r"[^a-zA-Z0-9._-]+",
        "_",
        f"{artist}-{title}",
    ).strip("_")[:100]
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
    return f"{base or 'song'}-{digest}.mp3"


async def cloudinary_cached_asset(public_id: str):
    require_cloudinary()

    try:
        return await asyncio.to_thread(
            cloudinary.api.resource,
            public_id,
            resource_type="video",
            type="upload",
        )
    except Exception as exc:
        # A missing resource is the normal cache-miss path. Any upload attempt
        # below will surface authentication/configuration errors if credentials
        # are invalid.
        message = str(exc).lower()
        if "not found" in message or "404" in message or "resource not found" in message:
            return None
        return None


@app.get("/")
async def root():
    return FileResponse(FRONTEND / "index.html")


SERVER_STARTED_AT=time.time()

@app.get("/api/system-status")
async def system_status():
    try:
        import psutil
        vm=psutil.virtual_memory()
        ram_used=vm.used
        ram_total=vm.total
        ram_percent=vm.percent
    except Exception:
        ram_used=ram_total=ram_percent=0
    try:
        disk=shutil.disk_usage("/")
        disk_used=disk.used
        disk_total=disk.total
        disk_percent=(disk.used/disk.total*100) if disk.total else 0
    except Exception:
        disk_used=disk_total=disk_percent=0
    uptime=time.time()-SERVER_STARTED_AT
    return {
        "uptime_seconds":round(uptime),
        "ram_used":ram_used,
        "ram_total":ram_total,
        "ram_percent":round(ram_percent,1),
        "disk_used":disk_used,
        "disk_total":disk_total,
        "disk_percent":round(disk_percent,1),
    }

@app.get("/api/status")
async def platform_status():
    try:
        import psutil
        memory=psutil.virtual_memory()
        disk=shutil.disk_usage(str(ROOT))
        boot=time.time()-psutil.boot_time()
        return {
            "runtime_seconds": int(boot),
            "ram_used": memory.used,
            "ram_total": memory.total,
            "ram_percent": memory.percent,
            "storage_used": disk.used,
            "storage_total": disk.total,
            "storage_free": disk.free,
        }
    except Exception as exc:
        return {"error": str(exc)}

@app.get("/api/timezone")
async def timezone(request: Request):
    forwarded=request.headers.get("x-forwarded-for","")
    client_ip=(forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else ""))
    if client_ip in {"127.0.0.1","::1","localhost"}:
        return {"timezone": ""}
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r=await client.get(f"https://ipapi.co/{client_ip}/json/")
            if r.status_code==200:
                data=r.json()
                return {"timezone":data.get("timezone",""),"ip":client_ip}
    except Exception:
        pass
    return {"timezone":""}

@app.get("/api/search")
async def search(q: str):
    query=q.strip()
    if not query:
        return {"result": []}

    async def call(client, provider):
        try:
            r=await client.get(provider+quote(query,safe=""))
            if r.status_code!=200:
                return None
            data=r.json()
            if data is None:
                return None
            return data
        except Exception:
            return None

    async with httpx.AsyncClient(timeout=httpx.Timeout(7.0,connect=3.0)) as client:
        results=await asyncio.gather(*(call(client,p) for p in SEARCH_APIS))
    for data in results:
        if data is not None:
            return data

    raise HTTPException(502,"All search providers are currently unavailable")


async def playlist_search(url: str):
    playlist_url=url.strip()
    if not playlist_url:
        raise HTTPException(400, "Spotify playlist URL is required")

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        for provider in PLAYLIST_APIS:
            try:
                r=await client.get(provider + quote(playlist_url, safe=""))
                if r.status_code != 200:
                    continue
                data=r.json()
                result=data.get("result") if isinstance(data, dict) else None
                meta=result if isinstance(result, dict) and isinstance(result.get("tracks"), list) else (data.get("data") if isinstance(data, dict) else {})
                tracks=(result or {}).get("tracks", []) if isinstance(result, dict) else []
                if not tracks and isinstance(data, dict):
                    tracks=data.get("tracks", [])
                if not isinstance(meta, dict):
                    meta={}
                if not isinstance(tracks, list) or not tracks:
                    continue

                normalized=[]
                for t in tracks:
                    if not isinstance(t, dict):
                        continue
                    track_url=t.get("url") or t.get("spotifyUrl") or t.get("link") or ""
                    if not track_url:
                        continue
                    normalized.append({
                        "title": t.get("title") or t.get("name") or "Unknown song",
                        "artist": t.get("artist") or t.get("artists") or "Unknown artist",
                        "thumbnail": t.get("thumbnail") or t.get("cover") or t.get("image") or meta.get("cover") or "",
                        "duration": t.get("duration") or "",
                        "durationMs": t.get("durationMs") or 0,
                        "id": t.get("id") or "",
                        "url": track_url,
                    })

                if normalized:
                    return {
                        "type": "playlist",
                        "id": meta.get("id") or "",
                        "name": meta.get("name") or meta.get("title") or "Spotify Playlist",
                        "owner": meta.get("owner") or "",
                        "cover": meta.get("cover") or "",
                        "total": meta.get("total") or len(normalized),
                        "count": len(normalized),
                        "tracks": normalized,
                    }
            except Exception:
                continue

    raise HTTPException(502, "Playlist providers are currently unavailable")

@app.get("/api/playlist")
async def playlist(url: str):
    return await playlist_search(url)

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


async def upload_to_cloudinary(temp_path: Path, public_id: str):
    require_cloudinary()

    def do_upload():
        return cloudinary.uploader.upload(
            str(temp_path),
            resource_type="video",
            type="upload",
            public_id=public_id,
            overwrite=False,
            unique_filename=False,
            use_filename=False,
        )

    try:
        return await asyncio.to_thread(do_upload)
    except Exception as exc:
        # Two simultaneous first requests can race. If another request won
        # the upload, return the existing Cloudinary asset instead of failing.
        existing = await cloudinary_cached_asset(public_id)
        if existing and existing.get("secure_url"):
            return existing
        raise HTTPException(502, f"Cloudinary upload failed: {exc}") from exc


@app.get("/api/download")
async def download(
    url: str,
    title: str = "",
    artist: str = "",
    thumbnail: str = "",
):
    if not url.strip():
        raise HTTPException(400, "Song URL is required")

    require_cloudinary()
    public_id = public_id_for(url)

    # Persistent cache: the source URL hash is the Cloudinary public ID, so
    # there is no database and no need to call the expiring download URL again.
    cached = await cloudinary_cached_asset(public_id)
    if cached and cached.get("secure_url"):
        return {
            "stream_url": cached["secure_url"],
            "cached": True,
            "title": title,
            "artist": artist,
            "thumbnail": thumbnail,
        }

    audio_url = await provider_audio_url(url)
    if not audio_url:
        raise HTTPException(502, "Download providers unavailable")

    filename = safe_name(
        title or "Unknown song",
        artist or "Unknown artist",
        url,
    )
    temp_path = TEMP_DIR / filename

    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            async with client.stream("GET", audio_url) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as out:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        out.write(chunk)

        uploaded = await upload_to_cloudinary(temp_path, public_id)
        secure_url = uploaded.get("secure_url") if uploaded else None
        if not secure_url:
            raise HTTPException(
                502,
                "Cloudinary upload completed without a playback URL",
            )

        return {
            "stream_url": secure_url,
            "cached": False,
            "title": title,
            "artist": artist,
            "thumbnail": thumbnail,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Audio storage failed: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)
