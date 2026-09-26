const state={songs:[],current:-1,loading:false,playRequest:0,autoMood:true,recommending:false,featured:[],featuredLoaded:false};
const $=id=>document.getElementById(id);
const audio=$("audioPlayer");
function esc(v=""){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));}
function normalize(data){const raw=data?.result||data?.tracks||data?.data||[];return (Array.isArray(raw)?raw:[]).map(t=>({title:t.title||t.name||t.trackName||"Unknown song",artist:t.artist||t.artists||"Unknown artist",thumbnail:t.thumbnail||t.cover||t.image||"",url:t.url||t.spotifyUrl||t.link||"",duration:t.duration||0})).filter(s=>s.url);}
function featuredCard(song,index){
  const thumb=song.thumbnail||"";
  const art=thumb?`<img src="${esc(thumb)}" alt="">`:`<div class="featured-placeholder">♪</div>`;
  return `<article class="featured-card">
    <div class="featured-art">${art}<span class="featured-number">${String(index+1).padStart(2,"0")}</span></div>
    <div class="featured-info"><strong>${esc(song.title)}</strong><small>${esc(song.artist)}</small></div>
    <button class="featured-play" data-featured-play="${index}" aria-label="Play ${esc(song.title)}">▶</button>
  </article>`;
}
function renderFeatured(){
  const box=$("featuredResults");
  box.innerHTML=state.featured.map(featuredCard).join("");
  $("featuredLoading").classList.add("hidden");
  $("featuredCount").textContent=FEATURED.length+" tracks";
}
async function resolveFeatured(){
  let cursor=0;
  async function worker(){
    while(cursor<FEATURED.length){
      const i=cursor++;
      const [title,artist]=FEATURED[i];
      try{
        const r=await fetch("/api/search?q="+encodeURIComponent(title+" "+artist));
        if(!r.ok)continue;
        const items=normalize(await r.json());
        if(items[0]){
          state.featured[i]={...state.featured[i],...items[0],title,artist};
          renderFeatured();
        }
      }catch{}
    }
  }
  await Promise.all([worker(),worker(),worker(),worker()]);
}
function loadFeatured(){
  state.featured=FEATURED.map(([title,artist])=>({title,artist,thumbnail:"",url:""}));
  state.featuredLoaded=true;
  renderFeatured();
  resolveFeatured();
}
async function playFeatured(index){
  let song=state.featured[index];
  if(!song)return;
  if(!song.url){
    try{
      const r=await fetch("/api/search?q="+encodeURIComponent(song.title+" "+song.artist));
      if(!r.ok)throw Error();
      const items=normalize(await r.json());
      if(items[0]){
        song={...song,...items[0],title:song.title,artist:song.artist};
        state.featured[index]=song;
        renderFeatured();
      }
    }catch{
      alert("This track could not be loaded right now.");
      return;
    }
  }
  if(!song.url)return;
  const existing=state.songs.findIndex(s=>s.url===song.url);
  if(existing>=0)play(existing);
  else{
    state.songs=[...state.featured.filter(s=>s.url)];
    render();
    const n=state.songs.findIndex(s=>s.url===song.url);
    if(n>=0)play(n);
  }
}
function render(){
  const box=$("results");box.innerHTML="";
  $("resultCount").textContent=state.songs.length?state.songs.length+" songs":"";
  if(!state.songs.length){$("emptyState").classList.remove("hidden");return}
  $("emptyState").classList.add("hidden");
  state.songs.forEach((s,i)=>{
    const el=document.createElement("article");el.className="song-card";
    el.innerHTML=`<img src="${esc(s.thumbnail)}" alt=""><div class="song-info"><strong>${esc(s.title)}</strong><small>${esc(s.artist)}</small></div><div class="song-actions"><button class="icon-btn play" data-play="${i}" aria-label="Play">▶</button><button class="icon-btn download-btn" data-download="${i}" aria-label="Download">↓</button></div>`;
    box.appendChild(el);
  });
}
async function search(){
  const q=$("searchInput").value.trim();if(!q)return;
  state.loading=true;
  $("results").innerHTML="";$("emptyState").classList.remove("hidden");$("emptyState").textContent="Searching…";
  try{
    const r=await fetch("/api/search?q="+encodeURIComponent(q));if(!r.ok)throw Error();
    state.songs=normalize(await r.json());$("emptyState").textContent=state.songs.length?"":"No songs found.";render();
    document.querySelector(".search-results-section").scrollIntoView({behavior:"smooth",block:"start"});
  }catch{$("emptyState").textContent="Search failed. Please try again."}
  finally{state.loading=false}
}
async function getAudio(song){
  const p=new URLSearchParams({url:song.url,title:song.title||"",artist:song.artist||"",thumbnail:song.thumbnail||""});
  const r=await fetch("/api/download?"+p);if(!r.ok)throw Error();
  const d=await r.json();return d.stream_url||d.download_link||d.download_url||d.result?.url||d.url||null;
}
async function findMoodSongs(song){
  if(!state.autoMood||state.recommending||!song?.title)return [];
  state.recommending=true;
  try{
    const queries=[song.artist+" "+song.title+" similar songs",song.artist+" songs",song.title+" similar"];
    const seen=new Set(state.songs.map(s=>s.url));const out=[];
    for(const q of queries){
      try{const r=await fetch("/api/search?q="+encodeURIComponent(q));if(!r.ok)continue;const items=normalize(await r.json());
        for(const s of items){if(s.url&&!seen.has(s.url)){seen.add(s.url);out.push(s)}if(out.length>=8)break}
      }catch{}
      if(out.length>=8)break;
    }
    if(out.length){state.songs.push(...out);render()}
    return out;
  }finally{state.recommending=false}
}
async function play(index){
  if(index<0||index>=state.songs.length)return;
  const request=++state.playRequest,song=state.songs[index];state.current=index;setPlayer(song);
  audio.pause();audio.removeAttribute("src");audio.load();
  try{
    const src=await getAudio(song);if(request!==state.playRequest)return;if(!src)throw Error("No stream URL");
    audio.src=src;audio.load();await audio.play();
    if(state.autoMood&&index===state.songs.length-1)findMoodSongs(song);
  }catch(e){if(request!==state.playRequest)return;console.error(e);$("playPauseButton").textContent="▶";$("fullPlay").textContent="▶";alert("Unable to play this song right now.")}
}
function setPlayer(s){$("miniThumb").src=s.thumbnail;$("miniTitle").textContent=s.title;$("miniArtist").textContent=s.artist;$("playerThumb").src=s.thumbnail;$("playerTitle").textContent=s.title;$("playerArtist").textContent=s.artist;$("miniPlayer").classList.remove("hidden")}
function toggle(){if(audio.paused)audio.play().catch(()=>{});else audio.pause()}
function next(){if(!state.songs.length)return;const n=state.current+1;if(n<state.songs.length)play(n);else if(state.autoMood&&state.songs[state.current])findMoodSongs(state.songs[state.current]).then(x=>x.length?play(state.current+1):null);else play(0)}
function prev(){if(!state.songs.length)return;play((state.current-1+state.songs.length)%state.songs.length)}
$("menuButton").onclick=()=>{$("sideMenu").classList.add("open");$("sideMenu").setAttribute("aria-hidden","false");$("menuButton").setAttribute("aria-expanded","true")};
$("closeMenu").onclick=()=>{$("sideMenu").classList.remove("open");$("sideMenu").setAttribute("aria-hidden","true");$("menuButton").setAttribute("aria-expanded","false")};
$("sideMenu").addEventListener("click",e=>{if(e.target===$("sideMenu"))$("closeMenu").click()});
$("searchButton").onclick=search;
$("searchInput").addEventListener("focus",()=>{$("featuredSection").classList.add("searching")});
$("searchInput").addEventListener("keydown",e=>{if(e.key==="Enter")search()});
$("featuredResults").addEventListener("click",e=>{const p=e.target.closest("[data-featured-play]");if(p)playFeatured(Number(p.dataset.featuredPlay))});
$("searchInput").addEventListener("keydown",e=>{if(e.key==="Enter")search()});
$("results").addEventListener("click",e=>{const p=e.target.closest("[data-play]"),d=e.target.closest("[data-download]");if(p)play(Number(p.dataset.play));if(d)download(Number(d.dataset.download))});
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
function fmt(s){if(!Number.isFinite(s))return"0:00";const m=Math.floor(s/60),sec=Math.floor(s%60).toString().padStart(2,"0");return m+":"+sec}const FEATURED=[["sorry i like you","burbank"],["Affection","Jinsang"],["Feather","Nujabes"],["5:32 PM","The Deli"],["This Is What Falling in Love Feels Like (Lofi)","JVKE"],["controlla","Idealism"],["Losing Interest","Itssvd feat. Shiloh Dynasty"],["I'm Closing My Eyes","Potsu feat. Shiloh Dynasty"],["Walk But In A Garden",".yu-utsu"],["Warm Glow","Hippo Campus"],["Iktara (Lofi Flip)","VIBIE & Amit Trivedi"],["Zara Zara (Lofi)","Bombay Jayashri"],["Jeene Laga Hoon (Lofi Mix)","Atif Aslam"],["Mehrama (Lofi Flip)","Darshan Raval & Silent Ocean"],["Heeriye (Lofi Mix)","Arijit Singh & Jasleen Royal"],["Hosanna (Lofi Flip)","Leon D'souza"],["Pehla Nasha (LoFi)","Udit Narayan"],["Tum Mile (Lofi Flip)","Pritam"],["Kabira (Lofi Reprise)","Tochi Raina & Rekha Bhardwaj"],["Channa Mereya (Lofi Chill)","Arijit Singh"],["Agar Tum Saath Ho (Lofi Flip)","Alka Yagnik & Arijit Singh"],["Tum Hi Ho (Slowed + Reverb)","Arijit Singh"],["Kun Faya Kun (Lofi Ambient)","A.R. Rahman"],["Ranjha (Lofi Version)","B Praak & Jasleen Royal"],["Raatan Lambiyan (Lofi Mix)","Jubin Nautiyal"]];
function featuredCard(song,index){
  const art=song.thumbnail?"<img src=\""+esc(song.thumbnail)+"\" alt=\"\">":"<div class=\"featured-placeholder\">♪</div>";
  return "<article class=\"featured-card\"><div class=\"featured-art\">"+art+"<span class=\"featured-number\">"+String(index+1).padStart(2,"0")+"</span></div><div class=\"featured-info\"><strong>"+esc(song.title)+"</strong><small>"+esc(song.artist)+"</small></div><button class=\"featured-play\" data-featured-play=\""+index+"\">▶</button></article>";
}
function renderFeatured(){ $("featuredResults").innerHTML=state.featured.map(featuredCard).join(""); $("featuredCount").textContent=FEATURED.length+" tracks"; }
async function resolveFeatured(){
  let cursor=0;
  async function worker(){
    while(cursor<FEATURED.length){ const i=cursor++; const [title,artist]=FEATURED[i]; try{ const r=await fetch("/api/search?q="+encodeURIComponent(title+" "+artist)); if(!r.ok)continue; const items=normalize(await r.json()); if(items[0]){state.featured[i]={...state.featured[i],...items[0],title,artist};renderFeatured();} }catch{} }
  }
  await Promise.all([worker(),worker(),worker(),worker()]);
}
function loadFeatured(){ state.featured=FEATURED.map(([title,artist])=>({title,artist,thumbnail:"",url:""})); renderFeatured(); resolveFeatured(); }
async function playFeatured(index){
  let song=state.featured[index]; if(!song)return;
  if(!song.url){ try{ const r=await fetch("/api/search?q="+encodeURIComponent(song.title+" "+song.artist)); if(!r.ok)throw Error(); const items=normalize(await r.json()); if(items[0]){song={...song,...items[0],title:song.title,artist:song.artist};state.featured[index]=song;renderFeatured();} }catch{alert("This track could not be loaded right now.");return;} }
  if(!song.url)return; state.songs=state.featured.filter(s=>s.url); render(); const n=state.songs.findIndex(s=>s.url===song.url); if(n>=0)play(n);
}

loadFeatured();
