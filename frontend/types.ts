export interface Song { title:string; artist:string; thumbnail:string; url:string; duration?:number; }
export interface SearchResponse { result?: Song[]; tracks?: Song[]; }
