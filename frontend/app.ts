import type {Song, SearchResponse} from './types';
export async function searchSongs(q:string):Promise<Song[]>{const r=await fetch('/api/search?q='+encodeURIComponent(q));if(!r.ok)throw new Error('search failed');const d=await r.json() as SearchResponse;return d.result??d.tracks??[];}
