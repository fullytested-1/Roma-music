from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

# CORS സെറ്റിംഗ്സ്
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# സെർച്ച് API-കളുടെ ലിസ്റ്റ്
SEARCH_APIS = [
    "https://jerrycoder.oggyapi.workers.dev/search/spotify?q=",
    "https://api.nexray.eu.cc/search/spotify?q=",
    "https://zellrayy.com/search/spotify?q="
]

# ഡൗൺലോഡ് API-കളുടെ ലിസ്റ്റ്
DOWNLOAD_APIS = [
    "https://jerrycoder.oggyapi.workers.dev/down/spotify?url=",
    "https://api.nexray.eu.cc/downloader/spotify?url=",
    "https://valora-api.vercel.app/download/spotify?url="
]

# റൂട്ട് ലിങ്ക് തുറക്കുമ്പോൾ കാണിക്കുന്ന ഹോം പേജ്
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Roma Music</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; text-align: center; padding: 50px; }
            h1 { color: #1ed760; }
            p { color: #b3b3b3; }
        </style>
    </head>
    <body>
        <h1>Roma Music Backend is Running!</h1>
        <p>All APIs and Fallback mechanisms are active and ready.</p>
    </body>
    </html>
    """

# സെർച്ച് എൻഡ്‌പോയിന്റ് (Fallbacks ഉൾപ്പെടെ)
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

# ഡൗൺലോഡ് എൻഡ്‌പോയിന്റ് (Fallbacks ഉൾപ്പെടെ)
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
