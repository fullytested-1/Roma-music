from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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

# 1. Frontend UI (Home Page with Black & Light Green Theme)
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Roma Music</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: #0f0f0f; 
                color: #ffffff; 
                text-align: center; 
                padding: 20px; 
            }
            h1 { color: #1ed760; margin-bottom: 20px; }
            .search-box { margin-bottom: 30px; }
            input { 
                padding: 12px 15px; 
                width: 300px; 
                border-radius: 25px; 
                border: 2px solid #222; 
                background: #181818;
                color: #fff;
                font-size: 16px;
                outline: none;
            }
            input:focus { border-color: #1ed760; }
            button { 
                padding: 12px 25px; 
                background: #1ed760; 
                color: #000; 
                font-weight: bold;
                border: none; 
                border-radius: 25px; 
                cursor: pointer; 
                font-size: 16px;
                margin-left: 10px;
            }
            button:hover { background: #1faa50; }
            .song-card { 
                background: #181818; 
                border: 1px solid #282828;
                margin: 12px auto; 
                padding: 12px; 
                width: 90%;
                max-width: 500px; 
                border-radius: 12px; 
                display: flex; 
                align-items: center; 
                justify-content: space-between; 
            }
            .song-card img { width: 60px; height: 60px; border-radius: 8px; object-fit: cover; }
            .details { text-align: left; margin-left: 15px; flex-grow: 1; }
            .details strong { color: #fff; font-size: 15px; }
            .details small { color: #b3b3b3; display: block; }
            .song-card button {
                background: transparent;
                color: #1ed760;
                border: 2px solid #1ed760;
                padding: 8px 15px;
                font-size: 14px;
                border-radius: 20px;
            }
            .song-card button:hover { background: #1ed760; color: #000; }
        </style>
    </head>
    <body>

        <h1>Roma Music</h1>
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search songs, artists...">
            <button onclick="searchSongs()">Search</button>
        </div>

        <div id="results"></div>

        <script>
            async function searchSongs() {
                const query = document.getElementById('searchInput').value;
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = "<p style='color:#b3b3b3;'>Searching...</p>";

                try {
                    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                    const data = await response.json();

                    resultsDiv.innerHTML = "";
                    const tracks = data.result || data.tracks || [];

                    if(tracks.length === 0) {
                        resultsDiv.innerHTML = "<p>No songs found!</p>";
                        return;
                    }

                    tracks.forEach(track => {
                        const title = track.title || track.name || track.trackName;
                        const artist = track.artist;
                        const thumbnail = track.thumbnail || track.cover || track.image;
                        const spotifyUrl = track.url || track.spotifyUrl;

                        const card = document.createElement('div');
                        card.className = 'song-card';
                        card.innerHTML = `
                            <img src="${thumbnail}" alt="Cover">
                            <div class="details">
                                <strong>${title}</strong>
                                <small>${artist}</small>
                            </div>
                            <button onclick="getDownloadLink('${spotifyUrl}')">Download</button>
                        `;
                        resultsDiv.appendChild(card);
                    });
                } catch (error) {
                    resultsDiv.innerHTML = "<p style='color:red;'>Error fetching songs.</p>";
                    console.error(error);
                }
            }

            async function getDownloadLink(spotifyUrl) {
                alert("Fetching download link...");
                try {
                    const response = await fetch(`/api/download?url=${encodeURIComponent(spotifyUrl)}`);
                    const data = await response.json();
                    
                    const downloadUrl = data.download_link || data.download_url || data.result?.url;

                    if (downloadUrl) {
                        window.open(downloadUrl, '_blank');
                    } else {
                        alert("Download link not found!");
                    }
                } catch (error) {
                    alert("Failed to get download link.");
                    console.error(error);
                }
            }
        </script>
    </body>
    </html>
    """

# 2. Backend Search API (with Fallback)
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

# 3. Backend Download API (with Fallback)
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
