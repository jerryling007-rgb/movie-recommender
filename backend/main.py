"""
FastAPI 后端服务 - 影片推荐系统 API
- 默认隐藏老电影（不主动推荐/不显示在首页）
- 详情页直接返回下载链接
- 支持按需获取下载链接
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from database import init_db, get_db, seed_categories
from scraper import BatchScraper, ACTIVE_CATEGORIES, CATEGORY_MAP
from recommender import recommender

# ========== 应用生命周期 ==========

async def _background_init():
    """后台初始化：数据库、分类、推荐向量、定时任务"""
    try:
        init_db()
        seed_categories()
        recommender.load_embeddings()
        from scheduler import start_scheduler
        start_scheduler()
        print("✅ 后台初始化完成")
    except Exception as e:
        print(f"⚠️ 后台初始化出错: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 立即让应用启动，接受健康检查
    asyncio.create_task(_background_init())
    yield
    from scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(
    title="影片推荐系统",
    description="基于 rrdynb.com 的智能影片推荐平台",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
import os as _os
STATIC_DIR = _os.environ.get(
    "STATIC_DIR",
    _os.path.join(_os.path.dirname(__file__), "..", "frontend", "dist"),
)
if _os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=_os.path.join(STATIC_DIR, "assets")), name="assets")


# ========== API 路由 ==========

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/categories")
async def get_categories():
    """获取分类列表（包含老电影+短剧+综艺，前端可选择性隐藏）"""
    with get_db() as db:
        cats = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
        return [dict(c) for c in cats]


@app.get("/api/movies")
async def get_movies(
    category: Optional[str] = Query(None, description="分类slug: movie/tv/classic/anime"),
    sub_category: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """影片列表查询 - 默认排除老电影（除非显式指定 category=classic）"""
    conditions = ["m.is_active = 1"]
    params = []

    if category:
        conditions.append("c.slug = ?")
        params.append(category)
    else:
        # 默认排除老电影
        conditions.append("c.slug != 'classic'")

    if sub_category:
        conditions.append("m.sub_category = ?")
        params.append(sub_category)
    if genre:
        conditions.append("m.genres LIKE ?")
        params.append(f"%{genre}%")
    if country:
        conditions.append("m.country LIKE ?")
        params.append(f"%{country}%")
    if year:
        conditions.append("m.year = ?")
        params.append(year)
    if keyword:
        conditions.append("(m.title LIKE ? OR m.genres LIKE ? OR m.director LIKE ? OR m.cast LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw])

    where = " AND ".join(conditions)

    allowed_sort = {
        "updated_at": "m.updated_at",
        "year": "m.year",
        "title": "m.title",
        "created_at": "m.created_at",
        "douban_rating": "m.douban_rating",
    }
    sort_col = allowed_sort.get(sort, "m.updated_at")
    sort_order = "DESC" if order == "desc" else "ASC"

    with get_db() as db:
        total = db.execute(
            f"SELECT COUNT(*) FROM movies m JOIN categories c ON m.category_id = c.id WHERE {where}",
            params,
        ).fetchone()[0]

        offset = (page - 1) * page_size
        rows = db.execute(
            f"""SELECT m.*, c.name as category_name, c.slug as category_slug
                FROM movies m JOIN categories c ON m.category_id = c.id
                WHERE {where}
                ORDER BY {sort_col} {sort_order}
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            "items": [dict(r) for r in rows],
        }


@app.get("/api/movies/{movie_id}")
async def get_movie_detail(movie_id: int):
    """获取影片详情 - 含下载链接"""
    with get_db() as db:
        movie = db.execute("""
            SELECT m.*, c.name as category_name, c.slug as category_slug
            FROM movies m JOIN categories c ON m.category_id = c.id
            WHERE m.id = ?
        """, (movie_id,)).fetchone()

        if not movie:
            raise HTTPException(status_code=404, detail="影片不存在")

        links = db.execute(
            "SELECT * FROM download_links WHERE movie_id = ? ORDER BY id",
            (movie_id,),
        ).fetchall()

        result = dict(movie)
        result["download_links"] = [dict(l) for l in links]
        return result


@app.get("/api/movies/{movie_id}/links")
async def get_or_fetch_links(movie_id: int):
    """获取下载链接 - 如果数据库中没有则从源站实时抓取"""
    with get_db() as db:
        movie = db.execute("SELECT id, detail_url, title FROM movies WHERE id = ?", (movie_id,)).fetchone()
        if not movie:
            raise HTTPException(status_code=404, detail="影片不存在")

        existing = db.execute(
            "SELECT * FROM download_links WHERE movie_id = ?", (movie_id,)
        ).fetchall()

        if existing:
            return {"movie_id": movie_id, "links": [dict(l) for l in existing], "cached": True}

    # 实时抓取
    scraper = BatchScraper()
    try:
        links = await scraper.fetch_links_for_movie(movie_id)
        await scraper.close()
        return {"movie_id": movie_id, "links": links, "cached": False}
    except Exception as e:
        await scraper.close()
        raise HTTPException(status_code=500, detail=f"获取下载链接失败: {str(e)}")


@app.get("/api/movies/{movie_id}/recommend")
async def get_recommendations(movie_id: int, top_k: int = Query(12, ge=1, le=50)):
    """AI智能推荐 - 排除老电影"""
    with get_db() as db:
        target = db.execute("""
            SELECT m.*, c.name as category_name, c.slug as category_slug
            FROM movies m JOIN categories c ON m.category_id = c.id
            WHERE m.id = ?
        """, (movie_id,)).fetchone()

        if not target:
            raise HTTPException(status_code=404, detail="影片不存在")

        recommended_ids = recommender.recommend(movie_id, top_k)

        if not recommended_ids:
            all_movies = db.execute("""
                SELECT m.id, m.title, m.genres, m.country, m.year
                FROM movies m JOIN categories c ON m.category_id = c.id
                WHERE m.is_active = 1 AND c.slug != 'classic'
            """).fetchall()
            recommended_ids = recommender.keyword_recommend(
                [dict(m) for m in all_movies], dict(target), top_k
            )

        if recommended_ids:
            placeholders = ",".join("?" * len(recommended_ids))
            rows = db.execute(f"""
                SELECT m.*, c.name as category_name, c.slug as category_slug
                FROM movies m JOIN categories c ON m.category_id = c.id
                WHERE m.id IN ({placeholders}) AND c.slug != 'classic'
            """, recommended_ids).fetchall()

            id_order = {rid: i for i, rid in enumerate(recommended_ids)}
            items = [dict(r) for r in rows]
            items.sort(key=lambda x: id_order.get(x["id"], 999))
        else:
            items = []

        return {"source": dict(target), "recommendations": items}


@app.get("/api/recommend/search")
async def recommend_by_text(
    q: str = Query(..., description="自然语言描述"),
    top_k: int = Query(12, ge=1, le=50),
):
    """根据文字描述搜索推荐 - 排除老电影"""
    recommended_ids = recommender.recommend_by_text(q, top_k)

    if not recommended_ids:
        return {"query": q, "recommendations": [], "message": "暂无匹配结果"}

    with get_db() as db:
        placeholders = ",".join("?" * len(recommended_ids))
        rows = db.execute(f"""
            SELECT m.*, c.name as category_name, c.slug as category_slug
            FROM movies m JOIN categories c ON m.category_id = c.id
            WHERE m.id IN ({placeholders}) AND c.slug != 'classic'
        """, recommended_ids).fetchall()

        id_order = {rid: i for i, rid in enumerate(recommended_ids)}
        items = [dict(r) for r in rows]
        items.sort(key=lambda x: id_order.get(x["id"], 999))

    return {"query": q, "recommendations": items}


@app.get("/api/stats")
async def get_stats():
    """获取统计数据 - 排除老电影"""
    with get_db() as db:
        total = db.execute("""
            SELECT COUNT(*) FROM movies m JOIN categories c ON m.category_id = c.id
            WHERE m.is_active = 1 AND c.slug != 'classic'
        """).fetchone()[0]
        by_category = db.execute("""
            SELECT c.name, c.slug, COUNT(*) as count
            FROM movies m JOIN categories c ON m.category_id = c.id
            WHERE m.is_active = 1 AND c.slug != 'classic'
            GROUP BY c.id ORDER BY c.id
        """).fetchall()
        by_year = db.execute("""
            SELECT m.year, COUNT(*) as count FROM movies m
            JOIN categories c ON m.category_id = c.id
            WHERE m.is_active = 1 AND c.slug != 'classic' AND m.year > 0
            GROUP BY m.year ORDER BY m.year DESC LIMIT 20
        """).fetchall()
        last_update = db.execute(
            "SELECT MAX(updated_at) as last_update FROM movies"
        ).fetchone()
        total_links = db.execute("SELECT COUNT(*) FROM download_links").fetchone()[0]

        return {
            "total": total,
            "by_category": [dict(r) for r in by_category],
            "by_year": [dict(r) for r in by_year],
            "last_update": last_update["last_update"] if last_update else None,
            "total_links": total_links,
        }


# ========== 抓取管理 API ==========

scraper_instance = None
scraping_status = {"running": False, "progress": "", "started_at": None}


def get_scraper():
    global scraper_instance
    if scraper_instance is None:
        scraper_instance = BatchScraper(None)
    return scraper_instance


@app.get("/api/crawl/status")
async def get_crawl_status():
    return scraping_status


@app.post("/api/crawl/start")
async def start_crawl(background_tasks: BackgroundTasks, full: bool = False):
    """手动触发抓取"""
    global scraping_status
    if scraping_status["running"]:
        return {"message": "抓取任务正在进行中", "status": scraping_status}

    from datetime import datetime as dt
    scraping_status = {"running": True, "progress": "准备中...", "started_at": dt.now().isoformat()}

    async def _crawl():
        global scraping_status, scraper_instance
        try:
            scraper = get_scraper()
            if full:
                scraping_status["progress"] = "全量同步中（不含老电影）..."
                new, updated = await scraper.full_sync(max_pages_per_category=93, fetch_links=True)
            else:
                scraping_status["progress"] = "快速同步首页..."
                new, updated = await scraper.quick_sync()

            scraping_status["running"] = False
            scraping_status["progress"] = f"完成: 新增 {new}, 更新 {updated}"
            scraping_status["result"] = {"new": new, "updated": updated}

            # 重建推荐向量
            with get_db() as db:
                movies = db.execute("""
                    SELECT m.* FROM movies m
                    JOIN categories c ON m.category_id = c.id
                    WHERE m.is_active = 1 AND c.slug != 'classic'
                """).fetchall()
                if movies:
                    recommender.build_embeddings([dict(m) for m in movies])

        except Exception as e:
            scraping_status["running"] = False
            scraping_status["progress"] = f"错误: {str(e)}"
            scraping_status["error"] = str(e)
        finally:
            if scraper_instance:
                await scraper_instance.close()
            scraper_instance = None

    background_tasks.add_task(_crawl)
    return {"message": "抓取任务已启动", "status": scraping_status}


# ========== 数据富化API ==========

enriching_status = {"running": False, "progress": "", "result": None, "error": None}


@app.get("/api/enrich/status")
async def enrich_status():
    return enriching_status


@app.post("/api/enrich/start")
async def start_enrich(batch_size: int = Query(20, ge=1, le=50), background_tasks: BackgroundTasks = None):
    """启动联网富化任务（搜豆瓣评分）"""
    if enriching_status["running"]:
        return {"message": "富化任务已在运行中", "status": enriching_status}

    from database import get_db as _get_db

    async def _enrich():
        global enriching_status
        enriching_status["running"] = True
        enriching_status["progress"] = "开始联网搜索豆瓣评分..."
        try:
            import httpx
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                with _get_db() as db:
                    # 缺评分的影片
                    movies = db.execute("""
                        SELECT m.id, m.title, m.year FROM movies m
                        JOIN categories c ON m.category_id = c.id
                        WHERE m.douban_rating = 0 AND c.slug != 'classic'
                        ORDER BY m.updated_at DESC LIMIT ?
                    """, (batch_size,)).fetchall()

                enriched = 0
                for i, m in enumerate(movies):
                    if i > 0 and i % 3 == 0:
                        await asyncio.sleep(2)

                    movie_id, title, year = m
                    query = f"{title} {year}" if year else title
                    enriching_status["progress"] = f"搜索中 ({i+1}/{len(movies)}): {title}"

                    try:
                        r = await client.get(
                            "https://www.douban.com/search",
                            params={"q": f"{query} 豆瓣评分", "cat": "1002"},
                            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
                        )
                        if r.status_code == 200:
                            import re
                            rating_m = re.search(r'<span\s+class="rating_nums"[^>]*>([\d.]+)</span>', r.text)
                            if rating_m:
                                rating = float(rating_m.group(1))
                                with _get_db() as db:
                                    db.execute("UPDATE movies SET douban_rating=? WHERE id=?", (rating, movie_id))
                                    db.commit()
                                enriched += 1
                                print(f"  ✅ {title} → ⭐{rating}")
                    except Exception as e:
                        print(f"  ❌ {title}: {e}")

                    await asyncio.sleep(0.6)

            enriching_status["running"] = False
            enriching_status["progress"] = f"完成: 富化了 {enriched}/{len(movies)} 部影片"
            enriching_status["result"] = {"enriched": enriched, "total": len(movies)}
        except Exception as e:
            enriching_status["running"] = False
            enriching_status["progress"] = f"错误: {str(e)}"
            enriching_status["error"] = str(e)

    background_tasks.add_task(_enrich)
    return {"message": "富化任务已启动", "status": enriching_status}


# ========== 前端静态文件 ==========

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if _os.path.exists(STATIC_DIR):
        file_path = _os.path.join(STATIC_DIR, full_path)
        if _os.path.exists(file_path) and _os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(_os.path.join(STATIC_DIR, "index.html"))
    return {"message": "前端未构建，请先构建前端"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
