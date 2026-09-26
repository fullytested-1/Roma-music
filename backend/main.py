from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

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
    "https://zellrayy.com/search/spotify?q="
]

DOWNLOAD_APIS = [
    "https://jerrycoder.oggyapi.workers.dev/down/spotify?url=",
    "https://api.nexray.eu.cc/downloader/spotify?url=",
    "https://valora-api.vercel.app/download/spotify?url="
]

@app.get("/api/search")
async def search_songs(q: str):
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
        
        raise HTTPException(status_code=500, detail="Ella Search API-kalum down aanu!")

@app.get("/api/download")
async def download_song(url: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        for api_url in DOWNLOAD_APIS:
            try:
                response = await client.get(f"{api_url}{url}")
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return data
            except Exception:
                continue
        
        raise HTTPException(status_code=500, detail="Ella Download API-kalum down aanu!")
