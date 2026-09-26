from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
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
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

@app.get("/")
async def read_root():
    return FileResponse(FRONTEND / "index.html")

@app.get("/api/search")
async def search_songs(q: str):
    if not q.strip():
        return {"result": []}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for api_url in SEARCH_APIS:
            try:
                response = await client.get(f"{api_url}{q}")
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return data
            except Exception:
                continue
    raise HTTPException(status_code=502, detail="Search providers unavailable")

@app.get("/api/download")
async def download_song(url: str):
    if not url.strip():
        raise HTTPException(status_code=400, detail="Song URL is required")
    async with httpx.AsyncClient(timeout=15.0) as client:
        for api_url in DOWNLOAD_APIS:
            try:
                response = await client.get(f"{api_url}{url}")
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return data
            except Exception:
                continue
    raise HTTPException(status_code=502, detail="Download providers unavailable")
