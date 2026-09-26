const state={songs:[],current:-1,loading:false,playRequest:0};
const $=id=>document.getElementById(id);
const audio=$("audioPlayer");

function esc(v=""){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));}
function normalize(data){const raw=data?.result||data?.tracks||data?.data||[];return (Array.isArray(raw)?raw:[]).map(t=>({title:t.title||t.name||t.trackName||"Unknown song",artist:t.artist||t.artists||"Unknown artist",thumbnail:t.thumbnail||t.cover||t.image||"",url:t.url||t.spotifyUrl||t.link||""}));}
function render(){const box=$("results");box.innerHTML="";$("resultCount").textContent=state.songs.length?state.songs.length+" songs":"";if(!state.songs.length){$("emptyState").classList.remove("hidden");return}$("emptyState").classList.add("hidden");
state.songs.forEach((s,i)=>{const el=document.createElement("article");el.className="song-card";el.innerHTML=`<img src="${esc(s.thumbnail)}" alt=""><div class="song-info"><strong>${esc(s.title)}</strong><small>${esc(s.artist)}</small></div><div class="song-actions"><button class="icon-btn play" data-play="${i}" aria-label="Play">▶</button><button class="icon-btn download-btn" data-download="${i}" aria-label="Download">↓</button></div>`;box.appendChild(el)})}
async function search(){const q=$("searchInput").value.trim();if(!q)return;state.loading=true;$("results").innerHTML="";$("emptyState").classList.remove("hidden");$("emptyState").textContent="Searching…";try{const r=await fetch("/api/search?q="+encodeURIComponent(q));if(!r.ok)throw Error();state.songs=normalize(await r.json());$("emptyState").textContent=state.songs.length?"":"No songs found.";render()}catch(e){$("emptyState").textContent="Search failed. Please try again."}finally{state.loading=false}}
async function getAudio(song){const params=new URLSearchParams({url:song.url,title:song.title||"",artist:song.artist||"",thumbnail:song.thumbnail||""});const r=await fetch("/api/download?"+params.toString());if(!r.ok)throw Error();const d=await r.json();return d.stream_url||d.download_link||d.download_url||d.result?.url||d.url||null}
async function play(index){
if(index<0||index>=state.songs.length)return;
const request=++state.playRequest;
const song=state.songs[index];
state.current=index;
setPlayer(song);
audio.pause();
audio.removeAttribute("src");
audio.load();
try{
const src=await getAudio(song);
if(request!==state.playRequest)return;
if(!src)throw Error("No stream URL");
audio.src=src;
audio.load();
await audio.play();
}catch(e){
if(request!==state.playRequest)return;
console.error("Roma playback error:",e);
$("playPauseButton").textContent="▶";
$("fullPlay").textContent="▶";
alert("Unable to play this song right now.");
}}
function setPlayer(s){$("miniThumb").src=s.thumbnail;$("miniTitle").textContent=s.title;$("miniArtist").textContent=s.artist;$("playerThumb").src=s.thumbnail;$("playerTitle").textContent=s.title;$("playerArtist").textContent=s.artist;$("miniPlayer").classList.remove("hidden")}
function toggle(){if(audio.paused){audio.play().catch(()=>{})}else audio.pause()}
function next(){if(!state.songs.length)return;play((state.current+1)%state.songs.length)}
function prev(){if(!state.songs.length)return;play((state.current-1+state.songs.length)%state.songs.length)}
$("searchButton").onclick=search;$("searchInput").addEventListener("keydown",e=>{if(e.key==="Enter")search()});
$("results").addEventListener("click",e=>{const p=e.target.closest("[data-play]");const d=e.target.closest("[data-download]");if(p)play(Number(p.dataset.play));if(d)download(Number(d.dataset.download))});
async function download(i){try{const src=await getAudio(state.songs[i]);if(src)window.open(src,"_blank");else alert("Download link not found.")}catch{alert("Download failed.")}}
$("miniInfo").onclick=()=>{$("fullPlayer").classList.add("open");$("fullPlayer").setAttribute("aria-hidden","false")};$("closePlayer").onclick=()=>{$("fullPlayer").classList.remove("open");$("fullPlayer").setAttribute("aria-hidden","true")};
$("playPauseButton").onclick=e=>{e.stopPropagation();toggle()};$("prevButton").onclick=e=>{e.stopPropagation();prev()};$("nextButton").onclick=e=>{e.stopPropagation();next()};$("fullPlay").onclick=toggle;$("fullPrev").onclick=prev;$("fullNext").onclick=next;
audio.addEventListener("play",()=>{$("playPauseButton").textContent="Ⅱ";$("fullPlay").textContent="Ⅱ"});audio.addEventListener("pause",()=>{$("playPauseButton").textContent="▶";$("fullPlay").textContent="▶"});
audio.addEventListener("ended",()=>next());
audio.addEventListener("timeupdate",()=>{const p=audio.duration?(audio.currentTime/audio.duration)*100:0;$("miniProgress").style.width=p+"%";$("seekBar").value=p;$("currentTime").textContent=fmt(audio.currentTime);$("totalTime").textContent=fmt(audio.duration)});
$("seekBar").addEventListener("input",e=>{if(audio.duration)audio.currentTime=(Number(e.target.value)/100)*audio.duration});
function fmt(s){if(!Number.isFinite(s))return"0:00";const m=Math.floor(s/60),sec=Math.floor(s%60).toString().padStart(2,"0");return m+":"+sec}
