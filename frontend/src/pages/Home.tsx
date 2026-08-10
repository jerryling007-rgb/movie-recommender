import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Flame, Calendar, Star, Loader2, RefreshCw, ArrowRight, Play, ChevronLeft, ChevronRight, Search, SlidersHorizontal } from "lucide-react";
import { api } from "../api";
import MovieCard from "../components/MovieCard";
import type { Movie, Stats, CrawlStatus } from "../types";

const CATEGORY_TABS = [
  { slug: "", label: "全部" },
  { slug: "movie", label: "电影" },
  { slug: "tv", label: "电视剧" },
  { slug: "anime", label: "动漫" },
  { slug: "variety", label: "综艺" },
  { slug: "short_drama", label: "短剧" },
];

const SORT_ROWS = [
  { sort: "created_at", label: "热门推荐", icon: Flame, desc: "最受欢迎的影片" },
  { sort: "year", label: "最新上映", icon: Calendar, desc: "按上映时间排列" },
  { sort: "douban_rating", label: "豆瓣高分", icon: Star, desc: "评分最高的影片" },
];

export default function Home() {
  const navigate = useNavigate();
  const [activeCat, setActiveCat] = useState("");
  const [movies, setMovies] = useState<Record<string, Movie[]>>({});
  const [stats, setStats] = useState<Stats | null>(null);
  const [crawlStatus, setCrawlStatus] = useState<CrawlStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [crawling, setCrawling] = useState(false);
  const [featured, setFeatured] = useState<Movie | null>(null);

  // 加载所有排序行的数据
  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = { page_size: "15" };
    if (activeCat) params.category = activeCat;

    const fetches = SORT_ROWS.map(async (row) => {
      const data = await api.getMovies({ ...params, sort: row.sort });
      return [row.sort, data.items] as [string, Movie[]];
    });

    Promise.all(fetches).then((results) => {
      const map: Record<string, Movie[]> = {};
      results.forEach(([key, items]) => { map[key] = items; });
      setMovies(map);
      const allMovies = results.flatMap(([, items]) => items);
      const heroMovie = allMovies.find((m) => m.poster_url) || allMovies[0] || null;
      setFeatured(heroMovie);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [activeCat]);

  // 统计
  useEffect(() => { api.getStats().then(setStats).catch(() => {}); }, []);

  // 抓取状态轮询
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const poll = () => {
      api.getCrawlStatus().then((s) => {
        setCrawlStatus(s);
        if (s.running) timer = setTimeout(poll, 3000);
        else if (s.result) { api.getStats().then(setStats); }
      });
    };
    poll();
    return () => clearTimeout(timer);
  }, []);

  const handleCrawl = async () => {
    setCrawling(true);
    await api.startCrawl(false);
    setCrawling(false);
  };

  const handleMovieClick = (movie: Movie) => {
    navigate(`/movie/${movie.id}`);
  };

  const handleRecommend = (movie: Movie) => {
    navigate(`/movie/${movie.id}?showRecommend=1`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="fade-in-up -mx-4">
      {/* ========== Hero Section ========== */}
      <section className="relative w-full h-[420px] md:h-[500px] overflow-hidden">
        {/* 动态光斑 */}
        <div className="hero-orb w-[500px] h-[500px] -top-20 left-[10%]" style={{ background: "radial-gradient(circle, rgba(245,158,11,0.5) 0%, transparent 70%)", animation: "ambientFloat1 20s ease-in-out infinite" }} />
        <div className="hero-orb w-[400px] h-[400px] top-[20%] right-[15%]" style={{ background: "radial-gradient(circle, rgba(168,85,247,0.4) 0%, transparent 70%)", animation: "ambientFloat2 25s ease-in-out infinite" }} />

        {/* 背景海报 */}
        {featured?.poster_url && (
          <img
            src={featured.poster_url}
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-center opacity-55 scale-110 blur-sm"
          />
        )}
        {/* 渐变遮罩 */}
        <div className="hero-gradient absolute inset-0" />
        <div className="hero-gradient-bottom absolute inset-0" />

        {/* 内容 */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 h-full flex flex-col justify-center">
          {featured ? (
            <div className="max-w-xl space-y-6">
              {/* 标签行 */}
              <div className="flex items-center gap-2.5">
                {activeCat && (
                  <span className="text-xs tag-gold px-3 py-1 rounded-full font-medium">
                    {CATEGORY_TABS.find((t) => t.slug === activeCat)?.label || activeCat}
                  </span>
                )}
                {featured.year > 0 && (
                  <span className="text-xs text-zinc-400 font-medium">{featured.year}</span>
                )}
                {(featured.douban_rating ?? 0) > 0 && (
                  <span className="rating-badge flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold">
                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                    {(featured.douban_rating ?? 0).toFixed(1)}
                  </span>
                )}
              </div>

              <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-tight">
                {featured.title}
              </h1>

              {featured.genres && (
                <div className="flex items-center gap-2 text-sm text-zinc-400">
                  <span>{featured.genres.replace(/\//g, " · ")}</span>
                  {featured.country && <span>· {featured.country}</span>}
                  {featured.runtime && <span>· {featured.runtime}</span>}
                </div>
              )}

              {featured.summary && (
                <p className="text-sm text-zinc-500 leading-relaxed line-clamp-2 max-w-md">
                  {featured.summary}
                </p>
              )}

              <div className="flex items-center gap-3 pt-1">
                <button
                  onClick={() => handleMovieClick(featured)}
                  className="magnetic-btn flex items-center gap-2 px-6 py-2.5 rounded-xl btn-gold text-sm"
                >
                  <Play className="w-4 h-4 fill-black" />
                  查看详情
                </button>
                <button
                  onClick={() => handleRecommend(featured)}
                  className="magnetic-btn flex items-center gap-2 px-5 py-2.5 rounded-xl btn-ghost text-sm"
                >
                  <Star className="w-4 h-4" />
                  找相似
                </button>
              </div>
            </div>
          ) : (
            <div className="max-w-xl">
              <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
                MovieRec
              </h1>
              <p className="mt-3 text-zinc-500 text-lg">
                收录 {stats?.total || 0} 部影片 · 每日同步更新
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ========== 筛选 + 操作栏 ========== */}
      <section className="max-w-7xl mx-auto px-4 -mt-6 relative z-20">
        <div className="glass-elevated p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          {/* 分类按钮 */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {CATEGORY_TABS.map((tab) => (
              <button
                key={tab.slug}
                onClick={() => setActiveCat(tab.slug)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                  activeCat === tab.slug
                    ? "bg-primary-500/12 text-primary-400 border border-primary-500/20"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.03] border border-transparent"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-3">
            {stats && (
              <span className="hidden sm:inline text-xs text-zinc-600">
                共 {stats.total} 部
              </span>
            )}
            <button
              onClick={handleCrawl}
              disabled={crawling || crawlStatus?.running}
              className="flex items-center gap-2 px-4 py-2 rounded-xl btn-ghost text-sm disabled:opacity-40"
            >
              {crawling || crawlStatus?.running ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {crawlStatus?.running ? "同步中..." : "更新数据"}
            </button>
          </div>
        </div>
      </section>

      {/* ========== 横向滚动影片行 ========== */}
      <div className="max-w-7xl mx-auto px-4 mt-10 space-y-12">
        {SORT_ROWS.map((row) => {
          const items = movies[row.sort] || [];
          const Icon = row.icon;

          return (
            <section key={row.sort}>
              {/* 行标题 */}
              <div className="flex items-center justify-between mb-5">
                <div>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-primary-500/8 flex items-center justify-center border border-primary-500/8">
                      <Icon className="w-4 h-4 text-primary-400" />
                    </div>
                    <h2 className="text-lg font-bold text-zinc-100">{row.label}</h2>
                  </div>
                  <p className="text-xs text-zinc-600 mt-0.5 ml-12">{row.desc}</p>
                </div>
                <button
                  onClick={() => navigate(`/browse?sort=${row.sort}`)}
                  className="flex items-center gap-1 text-xs text-zinc-600 hover:text-primary-400 transition-colors group"
                >
                  查看全部
                  <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>

              {items.length === 0 ? (
                <div className="py-10 text-center text-zinc-700 text-sm">暂无数据</div>
              ) : (
                <HorizontalScroller>
                  {items.map((movie) => (
                    <MovieCard
                      key={movie.id}
                      movie={movie}
                      compact
                      onRecommend={handleRecommend}
                    />
                  ))}
                </HorizontalScroller>
              )}

              {/* 分隔线 */}
              <div className="divider-glow mt-10" />
            </section>
          );
        })}
      </div>

      {/* ========== 底部统计概览 ========== */}
      {stats && (
        <section className="max-w-7xl mx-auto px-4 mt-12 mb-8">
          <div className="glass-panel rounded-2xl p-6">
            <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-5">数据概览</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatItem label="总计收录" value={stats.total} highlight />
              {stats.by_category?.map((cat) => (
                <StatItem key={cat.slug} label={cat.name} value={cat.count} />
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

/** 横向滚动容器 */
function HorizontalScroller({ children }: { children: React.ReactNode }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  const updateScrollButtons = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 10);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 10);
  };

  const scroll = (direction: "left" | "right") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: direction === "left" ? -400 : 400, behavior: "smooth" });
  };

  return (
    <div className="relative group/scroller">
      {canScrollLeft && (
        <button
          onClick={() => scroll("left")}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-black/60 backdrop-blur-xl flex items-center justify-center border border-white/[0.06] opacity-0 group-hover/scroller:opacity-100 transition-all -translate-x-2 hover:bg-black/80 hover:border-white/[0.12]"
        >
          <ChevronLeft className="w-5 h-5 text-zinc-300" />
        </button>
      )}

      <div
        ref={scrollRef}
        onScroll={updateScrollButtons}
        className="horizontal-row hide-scrollbar"
      >
        {children}
      </div>

      {canScrollRight && (
        <button
          onClick={() => scroll("right")}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-black/60 backdrop-blur-xl flex items-center justify-center border border-white/[0.06] opacity-0 group-hover/scroller:opacity-100 transition-all translate-x-2 hover:bg-black/80 hover:border-white/[0.12]"
        >
          <ChevronRight className="w-5 h-5 text-zinc-300" />
        </button>
      )}
    </div>
  );
}

function StatItem({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="text-center py-3">
      <p className={`text-2xl font-bold ${highlight ? "gradient-text" : "text-zinc-200"}`}>
        {value}
      </p>
      <p className="text-xs text-zinc-600 mt-1">{label}</p>
    </div>
  );
}
