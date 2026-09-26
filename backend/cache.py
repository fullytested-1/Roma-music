from pathlib import Path
import sqlite3
DB=Path(__file__).resolve().parent.parent/'data'/'roma.db'
def connect():
 DB.parent.mkdir(exist_ok=True)
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
 c.execute('CREATE TABLE IF NOT EXISTS songs(id INTEGER PRIMARY KEY,title TEXT,artist TEXT,thumbnail TEXT,source_url TEXT UNIQUE,audio_url TEXT,play_count INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,last_played_at TEXT)')
 c.execute('CREATE TABLE IF NOT EXISTS play_history(id INTEGER PRIMARY KEY,song_id INTEGER,played_at TEXT DEFAULT CURRENT_TIMESTAMP)');c.commit();return c
