import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Loader2, SlidersHorizontal } from "lucide-react";
import { api } from "../api";
import MovieCard from "../components/MovieCard";
import type { Movie } from "../types";

const CATEGORIES = [
  { slug: "", label: "全部" },
  { slug: "movie", label: "电影" },
  { slug: "tv", label: "电视剧" },
  { slug: "anime", label: "动漫" },
  { slug: "variety", label: "综艺" },
  { slug: "short_drama", label: "短剧" },
];

const SORT_OPTIONS = [
  { value: "created_at", label: "🔥 热度" },
  { value: "year", label: "📅 上映时间" },
  { value: "douban_rating", label: "⭐ 豆瓣评分" },
  { value: "updated_at", label: "🔄 更新时间" },
  { value: "title", label: "🔤 标题" },
];

export default function Browse() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [movies, setMovies] = useState<Movie[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  const page = parseInt(searchParams.get("page") || "1");
  const category = searchParams.get("category") || "";
  const keyword = searchParams.get("keyword") || "";
  const sort = searchParams.get("sort") || "created_at";
  const order = searchParams.get("order") || "desc";
  const genre = searchParams.get("genre") || "";
  const year = searchParams.get("year") || "";
  const country = searchParams.get("country") || "";

  const fetchMovies = useCallback(async () => {
    setLoading(true);
    const params: Record<string, string> = { page: String(page), page_size: "10", sort, order };
    if (category) params.category = category;
    if (keyword) params.keyword = keyword;
    if (genre) params.genre = genre;
    if (year) params.year = year;
    if (country) params.country = country;

    try {
      const data = await api.getMovies(params);
      setMovies(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [page, category, keyword, sort, order, genre, year, country]);

  useEffect(() => { fetchMovies(); }, [fetchMovies]);

  const updateParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value); else params.delete(key);
    if (key !== "page") params.set("page", "1");
    setSearchParams(params);
  };

  const goToPage = (p: number) => {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(p));
    setSearchParams(params);
  };

  return (
    <div className="space-y-6 fade-in-up">
      {/* 顶部 */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-zinc-100 tracking-tight">
          {keyword ? `搜索: "${keyword}"` : "影片浏览"}
          <span className="text-sm font-normal text-zinc-600 ml-2">共 {total} 部</span>
        </h1>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm transition-all ${
            showFilters ? "glass-panel text-primary-400" : "text-zinc-500 hover:text-zinc-300 btn-ghost"
          }`}
        >
          <SlidersHorizontal className="w-4 h-4" />
          筛选
        </button>
      </div>

      {/* 筛选面板 */}
      {showFilters && (
        <div className="glass-panel rounded-xl p-5 space-y-4 fade-in">
          <FilterRow label="分类">
            {CATEGORIES.map((c) => (
              <FilterChip key={c.slug} active={category === c.slug} onClick={() => updateParam("category", c.slug)}>
                {c.label}
              </FilterChip>
            ))}
          </FilterRow>

          <FilterRow label="排序">
            {SORT_OPTIONS.map((s) => (
              <FilterChip key={s.value} active={sort === s.value} onClick={() => updateParam("sort", s.value)}>
                {s.label}
              </FilterChip>
            ))}
            <FilterChip active={order === "asc"} onClick={() => updateParam("order", order === "asc" ? "desc" : "asc")}>
              {order === "asc" ? "升序 ↑" : "降序 ↓"}
            </FilterChip>
          </FilterRow>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-zinc-600 mb-1.5 block font-medium">年份</label>
              <input type="number" value={year} onChange={(e) => updateParam("year", e.target.value)} placeholder="如 2024" className="premium-input w-full px-3 py-2 text-sm placeholder-zinc-700" />
            </div>
            <div>
              <label className="text-xs text-zinc-600 mb-1.5 block font-medium">类型</label>
              <input type="text" value={genre} onChange={(e) => updateParam("genre", e.target.value)} placeholder="如 悬疑" className="premium-input w-full px-3 py-2 text-sm placeholder-zinc-700" />
            </div>
            <div>
              <label className="text-xs text-zinc-600 mb-1.5 block font-medium">国家</label>
              <input type="text" value={country} onChange={(e) => updateParam("country", e.target.value)} placeholder="如 美国" className="premium-input w-full px-3 py-2 text-sm placeholder-zinc-700" />
            </div>
          </div>
        </div>
      )}

      {/* 网格 */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-zinc-700" />
        </div>
      ) : movies.length === 0 ? (
        <div className="text-center py-20 text-zinc-600">
          <p className="text-lg font-medium mb-1">没有找到匹配的影片</p>
          <p className="text-sm text-zinc-700">试试调整筛选条件</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
          {movies.map((movie) => (<MovieCard key={movie.id} movie={movie} />))}
        </div>
      )}

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-6">
          <button onClick={() => goToPage(page - 1)} disabled={page <= 1} className="p-2.5 rounded-xl glass-card text-zinc-500 disabled:opacity-20 hover:text-zinc-300 transition-all disabled:cursor-not-allowed">
            <ChevronLeft className="w-4 h-4" />
          </button>
          {generatePages(page, totalPages).map((p, i) =>
            p === "..." ? (
              <span key={`dot-${i}`} className="text-zinc-700 px-1 text-sm">...</span>
            ) : (
              <button key={p} onClick={() => goToPage(p as number)} className={`w-9 h-9 rounded-xl text-sm font-medium transition-all ${
                page === p
                  ? "bg-primary-500/12 text-primary-400 border border-primary-500/20"
                  : "glass-card text-zinc-500 hover:text-zinc-300 hover:border-white/[0.06]"
              }`}>
                {p}
              </button>
            ),
          )}
          <button onClick={() => goToPage(page + 1)} disabled={page >= totalPages} className="p-2.5 rounded-xl glass-card text-zinc-500 disabled:opacity-20 hover:text-zinc-300 transition-all disabled:cursor-not-allowed">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="divider-glow mt-4" />
    </div>
  );
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-zinc-500 w-14 shrink-0 font-medium">{label}</span>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

function FilterChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
      active
        ? "bg-primary-500/12 text-primary-400 border border-primary-500/20"
        : "bg-zinc-900/40 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/60 border border-transparent"
    }`}>
      {children}
    </button>
  );
}

function generatePages(current: number, total: number): (number | string)[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | string)[] = [1];
  if (current > 3) pages.push("...");
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i);
  if (current < total - 2) pages.push("...");
  pages.push(total);
  return pages;
}
