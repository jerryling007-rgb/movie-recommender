import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Download, Sparkles, Loader2, Star, Clock, Film,
  Globe, Languages, Calendar, User, Users, Clapperboard,
  Copy, Check, Link2, Loader,
} from "lucide-react";
import { api } from "../api";
import MovieCard from "../components/MovieCard";
import type { Movie, DownloadLink } from "../types";

export default function Detail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [recommendations, setRecommendations] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [recLoading, setRecLoading] = useState(false);
  const [linksLoading, setLinksLoading] = useState(false);
  const [links, setLinks] = useState<DownloadLink[]>([]);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.getMovie(parseInt(id)).then((data) => {
      setMovie(data);
      setLinks(data.download_links || []);
      setLoading(false);
    });
  }, [id]);

  useEffect(() => {
    if (movie && searchParams.get("showRecommend") === "1") {
      loadRecommendations();
    }
  }, [movie]);

  useEffect(() => {
    if (movie && links.length === 0 && !linksLoading) {
      fetchLinks();
    }
  }, [movie]);

  const fetchLinks = async () => {
    if (!id) return;
    setLinksLoading(true);
    try {
      const data = await api.getLinks(parseInt(id));
      setLinks(data.links || []);
    } catch (e) { console.error(e); }
    setLinksLoading(false);
  };

  const loadRecommendations = async () => {
    if (!id) return;
    setRecLoading(true);
    try {
      const data = await api.getRecommendations(parseInt(id), 12);
      setRecommendations(data.recommendations);
    } catch (e) { console.error(e); }
    setRecLoading(false);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-700" />
      </div>
    );
  }

  if (!movie) {
    return <div className="text-center py-16 text-zinc-600">影片不存在</div>;
  }

  return (
    <div className="space-y-10 fade-in-up">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-zinc-600 hover:text-primary-400 transition-colors text-sm group">
        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
        返回
      </button>

      {/* 详情区域 */}
      <div className="flex flex-col md:flex-row gap-8">
        {/* 海报 */}
        <div className="w-52 shrink-0 mx-auto md:mx-0">
          <div className="poster-container rounded-2xl border border-white/[0.04] shadow-2xl">
            {movie.poster_url ? (
              <img src={movie.poster_url} alt={movie.title} className="w-full h-full object-cover" />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <Film className="w-16 h-16 text-zinc-800 opacity-30" />
              </div>
            )}
          </div>
        </div>

        {/* 信息 */}
        <div className="flex-1 space-y-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-zinc-100 tracking-tight">{movie.title}</h1>
            {movie.aka && <p className="text-sm text-zinc-600 mt-1.5">又名: {movie.aka}</p>}
          </div>

          {/* 类型标签 */}
          {movie.genres && (
            <div className="flex flex-wrap gap-2">
              {movie.genres.split(/[/\s]+/).filter(Boolean).map((g) => (
                <span key={g} className="tag-gold px-3 py-1 rounded-lg text-xs font-medium">{g}</span>
              ))}
            </div>
          )}

          {/* 元数据 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            {movie.director && <InfoRow icon={User} label="导演" value={movie.director} />}
            {movie.writers && <InfoRow icon={Users} label="编剧" value={movie.writers} />}
            {movie.cast && <InfoRow icon={Clapperboard} label="主演" value={movie.cast} />}
            {movie.country && <InfoRow icon={Globe} label="国家" value={movie.country} />}
            {movie.language && <InfoRow icon={Languages} label="语言" value={movie.language} />}
            {movie.release_date && <InfoRow icon={Calendar} label="上映" value={movie.release_date} />}
            {movie.episodes && <InfoRow icon={Film} label="集数" value={movie.episodes} />}
            {movie.runtime && <InfoRow icon={Clock} label="片长" value={movie.runtime} />}
            {movie.year > 0 && <InfoRow icon={Star} label="年份" value={String(movie.year)} />}
            {movie.douban_rating && movie.douban_rating > 0 && (
              <InfoRow icon={Star} label="豆瓣" value={`${movie.douban_rating.toFixed(1)} 分`} highlight />
            )}
          </div>

          {/* 简介 */}
          {movie.summary && (
            <div>
              <h3 className="text-sm font-semibold text-zinc-400 mb-2">剧情简介</h3>
              <p className="text-sm text-zinc-500 leading-relaxed">{movie.summary}</p>
            </div>
          )}
        </div>
      </div>

      {/* 下载链接区域 */}
      <div className="glass-panel rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-zinc-200 flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-500/8 flex items-center justify-center border border-primary-500/10">
              <Download className="w-4 h-4 text-primary-400" />
            </div>
            网盘下载
          </h2>
          {linksLoading && (
            <span className="flex items-center gap-1.5 text-xs text-zinc-600">
              <Loader className="w-3.5 h-3.5 animate-spin" />
              正在获取下载链接...
            </span>
          )}
        </div>

        {links.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {links.map((link, idx) => (
              <DownloadLinkCard key={idx} link={link} />
            ))}
          </div>
        ) : !linksLoading ? (
          <div className="text-center py-8 text-zinc-600">
            <p className="text-sm mb-2">暂无下载链接</p>
            <button onClick={fetchLinks} className="text-primary-400 hover:text-primary-300 text-sm font-medium transition-colors">
              点击重新获取
            </button>
          </div>
        ) : null}
      </div>

      {/* AI推荐 */}
      <div>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-zinc-200 flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-500/8 flex items-center justify-center border border-primary-500/10">
              <Sparkles className="w-4 h-4 text-primary-400" />
            </div>
            AI 智能推荐
          </h2>
          <button onClick={loadRecommendations} disabled={recLoading} className="magnetic-btn flex items-center gap-2 px-5 py-2.5 rounded-xl btn-gold text-sm disabled:opacity-50">
            {recLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {recommendations.length > 0 ? "换一批" : "找相似影片"}
          </button>
        </div>

        {recommendations.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {recommendations.map((m) => (<MovieCard key={m.id} movie={m} />))}
          </div>
        )}
      </div>

      <div className="divider-glow" />
    </div>
  );
}

function DownloadLinkCard({ link }: { link: DownloadLink }) {
  const [copied, setCopied] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  const platformClass = (platform: string) => {
    if (platform.includes("百度")) return "platform-baidu";
    if (platform.includes("夸克")) return "platform-quark";
    if (platform.includes("迅雷")) return "platform-xunlei";
    if (platform.includes("阿里")) return "platform-ali";
    return "bg-zinc-800/30 border border-zinc-700/30 text-zinc-400";
  };

  const platformIcon = (platform: string) => {
    if (platform.includes("迅雷")) return "⚡";
    return "🔗";
  };

  const pc = platformClass(link.platform);

  const copyUrl = () => {
    navigator.clipboard.writeText(link.url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyCode = () => {
    if (link.access_code) {
      navigator.clipboard.writeText(link.access_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  return (
    <div className={`dl-btn rounded-xl p-4 ${pc} backdrop-blur-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium flex items-center gap-1.5">
          <span className="text-base">{platformIcon(link.platform)}</span>
          {link.platform}
        </span>
        {link.access_code && (
          <button onClick={copyCode} className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
            {copiedCode ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
            提取码: {link.access_code}
          </button>
        )}
      </div>

      <div className="flex items-center gap-2">
        <a
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-zinc-300 text-sm transition-all border border-white/[0.04] hover:border-white/[0.08]"
        >
          <Link2 className="w-3.5 h-3.5" />
          打开链接
        </a>
        <button
          onClick={copyUrl}
          className="px-3 py-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-zinc-400 text-sm transition-all border border-white/[0.04] hover:border-white/[0.08]"
          title="复制链接"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, value, highlight }: { icon: any; label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-start gap-2">
      <Icon className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${highlight ? "text-amber-400" : "text-zinc-600"}`} />
      <span className="text-zinc-600 text-xs shrink-0 w-10">{label}</span>
      <span className={`text-sm leading-relaxed ${highlight ? "text-amber-300 font-semibold" : "text-zinc-400"}`}>{value}</span>
    </div>
  );
}
