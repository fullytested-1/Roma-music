const state={songs:[],current:-1,loading:false,playRequest:0,autoMood:true,recommending:false};
const HISTORY_KEY="roma_music_play_history_v1";
const $=id=>document.getElementById(id);
const audio=$("audioPlayer");

function esc(v=""){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));}
function normalize(data){const raw=data?.result||data?.tracks||data?.data||[];return (Array.isArray(raw)?raw:[]).map(t=>({title:t.title||t.name||t.trackName||"Unknown song",artist:t.artist||t.artists||"Unknown artist",thumbnail:t.thumbnail||t.cover||t.image||"",url:t.url||t.spotifyUrl||t.link||"",duration:t.duration||0})).filter(s=>s.url);}
function getHistory(){try{const x=JSON.parse(localStorage.getItem(HISTORY_KEY)||"[]");return Array.isArray(x)?x:[]}catch{return[]}}
function saveHistory(song){if(!song?.url)return;const h=getHistory().filter(s=>s.url!==song.url);h.unshift({title:song.title||"Unknown song",artist:song.artist||"Unknown artist",thumbnail:song.thumbnail||"",url:song.url||""});try{localStorage.setItem(HISTORY_KEY,JSON.stringify(h))}catch{}renderHistory()}
function historyCard(song,index){return `<article class="song-card"><img src="${esc(song.thumbnail)}" alt=""><div class="song-info"><strong>${esc(song.title)}</strong><small>${esc(song.artist)}</small></div><div class="song-actions"><button class="icon-btn play" data-history-play="${index}" aria-label="Play">▶</button></div></article>`}
function renderHistory(){const h=getHistory(),box=$("historyResults"),empty=$("historyEmpty");if(!h.length){box.innerHTML="";empty.classList.remove("hidden");return}empty.classList.add("hidden");box.innerHTML=h.map(historyCard).join("")}
function playHistory(i){const h=getHistory(),s=h[i];if(!s)return;const n=state.songs.findIndex(x=>x.url===s.url);if(n>=0)play(n);else{state.songs=[s];render();play(0)}}
function render(){const box=$("results");box.innerHTML="";$("resultCount").textContent=state.songs.length?state.songs.length+" songs":"";if(!state.songs.length){$("emptyState").classList.remove("hidden");return}$("emptyState").classList.add("hidden");state.songs.forEach((s,i)=>{const el=document.createElement("article");el.className="song-card";el.innerHTML=`<img src="${esc(s.thumbnail)}" alt=""><div class="song-info"><strong>${esc(s.title)}</strong><small>${esc(s.artist)}</small></div><div class="song-actions"><button class="icon-btn play" data-play="${i}" aria-label="Play">▶</button><button class="icon-btn download-btn" data-download="${i}" aria-label="Download">↓</button></div>`;box.appendChild(el)})}
async function search(){const q=$("searchInput").value.trim();if(!q)return;state.loading=true;$("results").innerHTML="";$("emptyState").classList.remove("hidden");$("emptyState").textContent="Searching…";try{const r=await fetch("/api/search?q="+encodeURIComponent(q));if(!r.ok)throw Error();state.songs=normalize(await r.json());$("emptyState").textContent=state.songs.length?"":"No songs found.";render()}catch{$("emptyState").textContent="Search failed. Please try again."}finally{state.loading=false}}
async function getAudio(song){const p=new URLSearchParams({url:song.url,title:song.title||"",artist:song.artist||"",thumbnail:song.thumbnail||""});const r=await fetch("/api/download?"+p);if(!r.ok)throw Error();const d=await r.json();return d.stream_url||d.download_link||d.download_url||d.result?.url||d.url||null}

async function findMoodSongs(song){
  if(!state.autoMood||state.recommending||!song?.title)return [];
  state.recommending=true;
  try{
    const queries=[song.artist+" "+song.title+" similar songs",song.artist+" songs",song.title+" similar"];
    const seen=new Set(state.songs.map(s=>s.url));
    const out=[];
    for(const q of queries){
      try{
        const r=await fetch("/api/search?q="+encodeURIComponent(q));
        if(!r.ok)continue;
        const items=normalize(await r.json());
        for(const s of items){
          if(s.url&&!seen.has(s.url)){seen.add(s.url);out.push(s)}
          if(out.length>=8)break;
        }
      }catch{}
      if(out.length>=8)break;
    }
    if(out.length){
      state.songs.push(...out);
      render();
    }
    return out;
  }finally{state.recommending=false}
}

async function play(index){
  if(index<0||index>=state.songs.length)return;
  const request=++state.playRequest;
  const song=state.songs[index];
  state.current=index;
  setPlayer(song);
  saveHistory(song);
  audio.pause();audio.removeAttribute("src");audio.load();
  try{
    const src=await getAudio(song);
    if(request!==state.playRequest)return;
    if(!src)throw Error("No stream URL");
    audio.src=src;audio.load();await audio.play();
    if(state.autoMood&&index===state.songs.length-1)findMoodSongs(song);
  }catch(e){
    if(request!==state.playRequest)return;
    console.error("Roma playback error:",e);
    $("playPauseButton").textContent="▶";$("fullPlay").textContent="▶";
    alert("Unable to play this song right now.");
  }
}
function setPlayer(s){$("miniThumb").src=s.thumbnail;$("miniTitle").textContent=s.title;$("miniArtist").textContent=s.artist;$("playerThumb").src=s.thumbnail;$("playerTitle").textContent=s.title;$("playerArtist").textContent=s.artist;$("miniPlayer").classList.remove("hidden")}
function toggle(){if(audio.paused)audio.play().catch(()=>{});else audio.pause()}
function next(){if(!state.songs.length)return;const n=state.current+1;if(n<state.songs.length)play(n);else if(state.autoMood&&state.songs[state.current])findMoodSongs(state.songs[state.current]).then(x=>x.length?play(state.current+1):null);else play(0)}
function prev(){if(!state.songs.length)return;play((state.current-1+state.songs.length)%state.songs.length)}
$("searchButton").onclick=search;
$("searchInput").addEventListener("keydown",e=>{if(e.key==="Enter")search()});
$("results").addEventListener("click",e=>{const p=e.target.closest("[data-play]"),d=e.target.closest("[data-download]");if(p)play(Number(p.dataset.play));if(d)download(Number(d.dataset.download))});
$("historyResults").addEventListener("click",e=>{const p=e.target.closest("[data-history-play]");if(p)playHistory(Number(p.dataset.historyPlay))});
$("clearHistory").onclick=()=>{localStorage.removeItem(HISTORY_KEY);renderHistory()};
async function download(i){try{const src=await getAudio(state.songs[i]);if(src)window.open(src,"_blank");else alert("Download link not found.")}catch{alert("Download failed.")}}
$("miniInfo").onclick=()=>{$("fullPlayer").classList.add("open");$("fullPlayer").setAttribute("aria-hidden","false")};
$("closePlayer").onclick=()=>{$("fullPlayer").classList.remove("open");$("fullPlayer").setAttribute("aria-hidden","true")};
$("playPauseButton").onclick=e=>{e.stopPropagation();toggle()};$("prevButton").onclick=e=>{e.stopPropagation();prev()};$("nextButton").onclick=e=>{e.stopPropagation();next()};
$("fullPlay").onclick=toggle;$("fullPrev").onclick=prev;$("fullNext").onclick=next;
$("autoplayToggle").onclick=()=>{state.autoMood=!state.autoMood;$("autoplayToggle").classList.toggle("on",state.autoMood);$("autoplayToggle").setAttribute("aria-pressed",String(state.autoMood));$("autoplayBadge").textContent=state.autoMood?"AUTO • ON":"AUTO • OFF";$("upNextLabel").textContent=state.autoMood?"Up next will be picked automatically":"Auto mood is off"};
audio.addEventListener("play",()=>{$("playPauseButton").textContent="Ⅱ";$("fullPlay").textContent="Ⅱ"});
audio.addEventListener("pause",()=>{$("playPauseButton").textContent="▶";$("fullPlay").textContent="▶"});
audio.addEventListener("ended",()=>next());
audio.addEventListener("timeupdate",()=>{const p=audio.duration?(audio.currentTime/audio.duration)*100:0;$("miniProgress").style.width=p+"%";$("seekBar").value=p;$("currentTime").textContent=fmt(audio.currentTime);$("totalTime").textContent=fmt(audio.duration)});
$("seekBar").addEventListener("input",e=>{if(audio.duration)audio.currentTime=(Number(e.target.value)/100)*audio.duration});
function fmt(s){if(!Number.isFinite(s))return"0:00";const m=Math.floor(s/60),sec=Math.floor(s%60).toString().padStart(2,"0");return m+":"+sec}
renderHistory();
