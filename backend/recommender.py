"""
AI智能推荐引擎
基于 TF-IDF + 余弦相似度实现智能推荐（无需下载外部模型）
"""
import os
import pickle
import numpy as np
from typing import Optional

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model_cache")
EMBEDDING_FILE = os.path.join(MODEL_DIR, "tfidf_matrix.pkl")


class MovieRecommender:
    """影片智能推荐引擎 - TF-IDF 方案"""

    def __init__(self):
        self.tfidf_matrix: Optional[np.ndarray] = None
        self.movie_ids: list[int] = []
        self.movie_texts: list[str] = []
        self._vectorizer = None

    def _build_text(self, movie: dict) -> str:
        """构建用于TF-IDF的文本表示"""
        parts = []
        # 标题权重最高（重复3次）
        if movie.get("title"):
            parts.append(movie["title"] * 3)
        if movie.get("genres"):
            parts.append(movie["genres"].replace("/", " "))
        if movie.get("director"):
            parts.append(movie["director"])
        if movie.get("cast"):
            parts.append(movie["cast"])
        if movie.get("country"):
            parts.append(movie["country"].replace("/", " "))
        if movie.get("language"):
            parts.append(movie["language"])
        if movie.get("summary"):
            parts.append(movie["summary"][:300])
        if movie.get("aka"):
            parts.append(movie["aka"])
        return " ".join(parts)

    def build_embeddings(self, movies: list[dict]):
        """为所有影片构建 TF-IDF 矩阵"""
        from sklearn.feature_extraction.text import TfidfVectorizer

        os.makedirs(MODEL_DIR, exist_ok=True)

        self.movie_ids = [m["id"] for m in movies]
        self.movie_texts = [self._build_text(m) for m in movies]

        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
            min_df=1,
        )

        self.tfidf_matrix = self._vectorizer.fit_transform(self.movie_texts)

        # 保存完整 vectorizer（含 IDF 权重）
        import pickle as pkl
        with open(EMBEDDING_FILE, "wb") as f:
            pkl.dump({
                "matrix": self.tfidf_matrix,
                "movie_ids": self.movie_ids,
                "movie_texts": self.movie_texts,
                "vectorizer": self._vectorizer,
            }, f)

        print(f"✅ 已构建 {len(self.movie_ids)} 条影片的 TF-IDF 矩阵 (维度: {self.tfidf_matrix.shape})")

    def load_embeddings(self) -> bool:
        """加载已保存的 TF-IDF 矩阵"""
        if os.path.exists(EMBEDDING_FILE):
            try:
                with open(EMBEDDING_FILE, "rb") as f:
                    data = pickle.load(f)
                    self.tfidf_matrix = data["matrix"]
                    self.movie_ids = data["movie_ids"]
                    self.movie_texts = data.get("movie_texts", [])
                    self._vectorizer = data.get("vectorizer", None)
                return True
            except Exception:
                return False
        return False

    def recommend(self, movie_id: int, top_k: int = 12) -> list[int]:
        """根据影片ID推荐相似影片"""
        if self.tfidf_matrix is None or not self.movie_ids:
            if not self.load_embeddings():
                return []

        try:
            idx = self.movie_ids.index(movie_id)
        except ValueError:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        query_vec = self.tfidf_matrix[idx]
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # 排除自身
        similarities[idx] = -1

        top_indices = np.argsort(similarities)[::-1][:top_k]
        # 过滤相似度太低的
        result = [self.movie_ids[i] for i in top_indices if similarities[i] > 0.05]
        return result

    def recommend_by_text(self, query: str, top_k: int = 12) -> list[int]:
        """根据文字描述推荐影片"""
        if self.tfidf_matrix is None or not self.movie_ids:
            if not self.load_embeddings():
                return []

        if self._vectorizer is None:
            return []

        query_vec = self._vectorizer.transform([query])
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [self.movie_ids[i] for i in top_indices if similarities[i] > 0.01]

    @staticmethod
    def keyword_recommend(movies: list[dict], target_movie: dict, top_k: int = 12) -> list[int]:
        """基于关键词的简单推荐（最终降级方案）"""
        def score(a, b):
            s = 0
            if a.get("genres") and b.get("genres"):
                a_genres = set(a["genres"].replace("/", " ").split())
                b_genres = set(b["genres"].replace("/", " ").split())
                s += len(a_genres & b_genres) * 3
            if a.get("country") == b.get("country") and a.get("country"):
                s += 2
            if a.get("year") and b.get("year") and abs(a["year"] - b["year"]) <= 3:
                s += 1
            return s

        scores = [(score(m, target_movie), m["id"]) for m in movies if m["id"] != target_movie["id"]]
        scores.sort(key=lambda x: x[0], reverse=True)
        return [sid for _, sid in scores[:top_k] if _ > 1]


# 全局实例
recommender = MovieRecommender()
