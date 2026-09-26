async function searchSongs(): Promise<void> {
    const query = (document.getElementById('searchInput') as HTMLInputElement).value;
    const resultsDiv = document.getElementById('results')!;
    resultsDiv.innerHTML = "Searching...";

    try {
        const response = await fetch(`http://127.0.0.1:8000/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        resultsDiv.innerHTML = "";
        const tracks = data.result || data.tracks || [];

        tracks.forEach((track: any) => {
            const title = track.title || track.name || track.trackName;
            const artist = track.artist;
            const thumbnail = track.thumbnail || track.cover || track.image;
            const spotifyUrl = track.url || track.spotifyUrl;

            const card = document.createElement('div');
            card.className = 'song-card';
            card.innerHTML = `
                <img src="${thumbnail}" alt="Cover">
                <div class="details">
                    <strong>${title}</strong><br>
                    <small>${artist}</small>
                </div>
                <button onclick="getDownloadLink('${spotifyUrl}')">Download</button>
            `;
            resultsDiv.appendChild(card);
        });
    } catch (error) {
        resultsDiv.innerHTML = "Error fetching songs.";
        console.error(error);
    }
}

async function getDownloadLink(spotifyUrl: string): Promise<void> {
    alert("Fetching download link...");
    try {
        const response = await fetch(`http://127.0.0.1:8000/api/download?url=${encodeURIComponent(spotifyUrl)}`);
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
  
