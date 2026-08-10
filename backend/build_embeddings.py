"""构建 TF-IDF 推荐嵌入矩阵"""
import sys
sys.path.insert(0, '.')

from database import init_db, get_db
from recommender import recommender

def main():
    init_db()
    
    with get_db() as db:
        movies = db.execute("""
            SELECT m.* FROM movies m
            JOIN categories c ON m.category_id = c.id
            WHERE m.is_active = 1 AND c.slug != 'classic'
        """).fetchall()
    
    print(f"📊 加载 {len(movies)} 条影片数据...")
    
    recommender.build_embeddings([dict(m) for m in movies])
    
    # Quick test
    test_movie = movies[0]
    recs = recommender.recommend(test_movie["id"], top_k=5)
    print(f"🧪 测试推荐: {test_movie['title']} → {len(recs)} 条相似影片")

if __name__ == "__main__":
    main()
