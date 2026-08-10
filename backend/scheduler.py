"""
定时任务调度器
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


def start_scheduler():
    """启动定时抓取任务"""
    try:
        from scraper import BatchScraper
        from database import get_db
        from recommender import recommender

        async def daily_sync():
            print("\n⏰ 定时任务: 每日更新开始...")
            try:
                scraper = BatchScraper(None)
                new, updated = await scraper.quick_sync()
                print(f"  ✅ 每日更新完成: 新增 {new}, 更新 {updated}")

                # 如果新增较多，更新推荐模型
                if new > 5:
                    with get_db() as db:
                        movies = db.execute("""
                            SELECT m.* FROM movies m
                            JOIN categories c ON m.category_id = c.id
                            WHERE m.is_active = 1 AND c.slug != 'classic'
                        """).fetchall()
                        if movies:
                            recommender.build_embeddings([dict(m) for m in movies])
            except Exception as e:
                print(f"  ❌ 每日更新失败: {e}")
            finally:
                await scraper.close()

        # 每天早上9:00运行
        scheduler.add_job(
            daily_sync,
            trigger=CronTrigger(hour=9, minute=0),
            id="daily_sync",
            name="每日影片更新",
            replace_existing=True,
        )

        scheduler.start()
        print("✅ 定时任务已启动 (每日 09:00)")
    except Exception as e:
        print(f"⚠️ 定时任务启动失败: {e}")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
