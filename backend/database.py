"""
数据库模型 - SQLite
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "movies.db")


def get_db_path():
    return DB_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                slug TEXT NOT NULL UNIQUE,
                url_path TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                title_en TEXT DEFAULT '',
                category_id INTEGER NOT NULL,
                sub_category TEXT NOT NULL DEFAULT 'latest',
                poster_url TEXT DEFAULT '',
                detail_url TEXT NOT NULL UNIQUE,
                director TEXT DEFAULT '',
                writers TEXT DEFAULT '',
                cast TEXT DEFAULT '',
                genres TEXT DEFAULT '',
                country TEXT DEFAULT '',
                language TEXT DEFAULT '',
                release_date TEXT DEFAULT '',
                episodes TEXT DEFAULT '',
                runtime TEXT DEFAULT '',
                aka TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                resource_info TEXT DEFAULT '',
                year INTEGER DEFAULT 0,
                douban_rating REAL DEFAULT 0,
                source_id TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS download_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                url TEXT DEFAULT '',
                access_code TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS crawl_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_slug TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                items_found INTEGER DEFAULT 0,
                items_new INTEGER DEFAULT 0,
                items_updated INTEGER DEFAULT 0,
                error_message TEXT DEFAULT '',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_movies_category ON movies(category_id);
            CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year);
            CREATE INDEX IF NOT EXISTS idx_movies_douban_rating ON movies(douban_rating);
            CREATE INDEX IF NOT EXISTS idx_movies_genres ON movies(genres);
            CREATE INDEX IF NOT EXISTS idx_movies_updated ON movies(updated_at);
            CREATE INDEX IF NOT EXISTS idx_movies_active ON movies(is_active);
            CREATE INDEX IF NOT EXISTS idx_movies_source_id ON movies(source_id);
            CREATE INDEX IF NOT EXISTS idx_download_links_movie ON download_links(movie_id);

            -- 初始分类数据
            INSERT OR IGNORE INTO categories (name, slug, url_path) VALUES
                ('电影', 'movie', '/movie/'),
                ('电视剧', 'tv', '/dianshiju/'),
                ('老电影', 'classic', '/zongyi/'),
                ('动漫', 'anime', '/dongman/'),
                ('短剧', 'short_drama', '/dianshiju/'),
                ('综艺', 'variety', '/dianshiju/');
        """)

        # 迁移：添加 douban_rating 列（兼容旧数据库）
        try:
            db.execute("ALTER TABLE movies ADD COLUMN douban_rating REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass


def seed_categories():
    init_db()
