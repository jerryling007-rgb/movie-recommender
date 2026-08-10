"""
影片数据富化工具 — 通过互联网搜索补全豆瓣评分、上映年份等缺失数据
"""
import sqlite3
import asyncio
import re
import time
from urllib.parse import quote

import httpx

DB_PATH = "movies.db"
DOUBAN_SEARCH = "https://www.douban.com/search"
TMDB_SEARCH = "https://api.themoviedb.org/3/search/multi"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def get_missing_movies(limit: int = 50, offset: int = 0):
    """获取缺豆瓣评分的影片"""
    db = get_db()
    rows = db.execute(
        """SELECT m.id, m.title, m.year, m.genres, m.country, c.name as cat_name
           FROM movies m JOIN categories c ON m.category_id = c.id
           WHERE m.douban_rating = 0
           ORDER BY m.updated_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


async def search_douban(client: httpx.AsyncClient, title: str, year: int = 0) -> dict | None:
    """在豆瓣搜索影片，返回 {rating, year}"""
    query = title
    if year:
        query = f"{title} {year}"
    
    try:
        r = await client.get(
            DOUBAN_SEARCH,
            params={"q": query, "cat": "1002"},  # cat=1002 是电影
            headers=HEADERS,
            timeout=10,
        )
        if r.status_code != 200:
            return None
        
        html = r.text
        
        # 提取评分: <span class="rating_nums">X.X</span>  或  <span class="rating_nums">X.X</span>
        rating_match = re.search(r'<span\s+class="rating_nums"[^>]*>([\d.]+)</span>', html)
        
        # 提取第一个结果的标题和年份
        title_match = re.search(r'<a[^>]*class="nbg"[^>]*title="([^"]*)"', html)
        
        result = {}
        if rating_match:
            result["rating"] = float(rating_match.group(1))
        if title_match:
            # 尝试从标题中提取年份
            yr_match = re.search(r'\((\d{4})\)', title_match.group(1))
            if yr_match:
                result["year"] = int(yr_match.group(1))
        
        return result if result else None
        
    except Exception as e:
        print(f"  搜索失败 '{query}': {e}")
        return None


async def search_tmdb(client: httpx.AsyncClient, title: str, year: int = 0, api_key: str = "") -> dict | None:
    """通过 TMDB API 搜索影片评分"""
    if not api_key:
        return None
    
    try:
        params = {
            "api_key": api_key,
            "query": title,
            "language": "zh-CN",
        }
        if year:
            params["year"] = year
        
        r = await client.get(TMDB_SEARCH, params=params, timeout=10)
        if r.status_code != 200:
            return None
        
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None
        
        first = results[0]
        result = {"rating": round(first.get("vote_average", 0), 1)}
        
        release = first.get("release_date") or first.get("first_air_date")
        if release:
            result["year"] = int(release[:4])
        
        return result if result.get("rating", 0) > 0 else None
        
    except Exception as e:
        print(f"  TMDB搜索失败 '{title}': {e}")
        return None


def update_movie(movie_id: int, rating: float | None = None, year: int | None = None):
    """更新影片数据"""
    db = get_db()
    if rating is not None:
        db.execute("UPDATE movies SET douban_rating = ? WHERE id = ?", (rating, movie_id))
    if year is not None:
        db.execute("UPDATE movies SET year = ? WHERE id = ?", (year, movie_id))
    db.commit()
    db.close()


async def enrich_batch(limit: int = 50, tmdb_key: str = ""):
    """批量富化一批影片"""
    movies = get_missing_movies(limit)
    if not movies:
        print("✅ 所有影片数据已完整！")
        return
    
    print(f"📋 开始富化 {len(movies)} 部影片...")
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        enriched = 0
        for i, movie in enumerate(movies):
            if i > 0 and i % 5 == 0:
                print(f"  进度: {i}/{len(movies)}, 已富化 {enriched} 部")
                await asyncio.sleep(2)  # 每5部休息2秒
            else:
                await asyncio.sleep(0.8)  # 每次搜索间隔0.8秒
            
            # 尝试豆瓣搜索
            result = await search_douban(client, movie["title"], movie["year"])
            
            # 如果豆瓣失败，尝试TMDB
            if not result and tmdb_key:
                result = await search_tmdb(client, movie["title"], movie["year"], tmdb_key)
            
            if result:
                update_movie(
                    movie["id"],
                    rating=result.get("rating"),
                    year=result.get("year"),
                )
                enriched += 1
                rating_str = f"⭐{result['rating']}" if result.get("rating") else ""
                year_str = f"📅{result['year']}" if result.get("year") else ""
                print(f"  ✅ {movie['title']} {rating_str} {year_str}")
    
    print(f"\n🎉 完成！富化了 {enriched}/{len(movies)} 部影片")


def stats():
    """查看富化统计"""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    with_rating = db.execute(
        "SELECT COUNT(*) FROM movies WHERE douban_rating > 0"
    ).fetchone()[0]
    db.close()
    return total, with_rating


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        total, rated = stats()
        print(f"总影片: {total}, 有评分: {rated} ({rated*100//max(total,1)}%)")
    else:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
        tmdb_key = sys.argv[2] if len(sys.argv) > 2 else ""
        asyncio.run(enrich_batch(limit, tmdb_key))
