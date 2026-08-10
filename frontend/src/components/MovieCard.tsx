import { useNavigate } from "react-router-dom";
import { Star, Clock, Play } from "lucide-react";
import type { Movie } from "../types";

interface Props {
  movie: Movie;
  compact?: boolean;
  onRecommend?: (movie: Movie) => void;
}

export default function MovieCard({ movie, compact, onRecommend }: Props) {
  const navigate = useNavigate();

  return (
    <div
      className="movie-card group cursor-pointer relative"
      style={{ width: compact ? 156 : "auto" }}
      onClick={() => navigate(`/movie/${movie.id}`)}
    >
      {/* 海报 */}
      <div
        className="poster-container relative"
        style={{ borderRadius: compact ? "10px" : "12px" }}
      >
        {movie.poster_url ? (
          <img
            src={movie.poster_url}
            alt={movie.title}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : null}
        <div className="poster-overlay" />

        {/* 无海报占位 */}
        {!movie.poster_url && (
          <div className="absolute inset-0 flex items-center justify-center text-zinc-800">
            <FilmPlaceholder />
          </div>
        )}

        {/* 豆瓣评分角标 - 左上角 */}
        {(movie.douban_rating ?? 0) > 0 && (
          <div className="absolute top-2.5 left-2.5 rating-badge flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-bold shadow-lg">
            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
            {(movie.douban_rating ?? 0).toFixed(1)}
          </div>
        )}

        {/* 年份角标 - 底部 */}
        {movie.year > 0 && (
          <div className="absolute bottom-2.5 left-2.5 text-[11px] text-zinc-200 bg-black/50 backdrop-blur-md px-1.5 py-0.5 rounded-md font-medium border border-white/[0.04]">
            {movie.year}
          </div>
        )}

        {/* 悬停播放按钮 */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-400">
          <div className="w-12 h-12 rounded-full bg-amber-500/90 flex items-center justify-center shadow-xl shadow-amber-500/20 transform scale-75 group-hover:scale-100 transition-all duration-400">
            <Play className="w-5 h-5 text-black ml-0.5" />
          </div>
        </div>

        {/* 悬停推荐按钮 */}
        {onRecommend && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRecommend(movie);
            }}
            className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-all duration-300 bg-black/60 hover:bg-black/80 text-zinc-200 text-[11px] px-2.5 py-1 rounded-lg backdrop-blur-lg font-medium border border-white/[0.08] hover:border-white/[0.14]"
          >
            找相似
          </button>
        )}
      </div>

      {/* 信息区 */}
      <div className={`${compact ? "p-2.5" : "p-3"} space-y-1.5`}>
        <h3
          className={`${compact ? "text-xs" : "text-sm"} font-medium text-zinc-200 line-clamp-1 tracking-wide`}
          title={movie.title}
        >
          {movie.title}
        </h3>

        {!compact && movie.genres && (
          <div className="flex flex-wrap gap-1">
            {movie.genres
              .split(/[/\s]+/)
              .slice(0, 2)
              .filter(Boolean)
              .map((g) => (
                <span key={g} className="text-[10px] px-2 py-0.5 rounded-md tag-dark">
                  {g}
                </span>
              ))}
          </div>
        )}

        <div className={`flex items-center gap-2 ${compact ? "text-[10px]" : "text-xs"} text-zinc-600`}>
          {!compact && (movie.douban_rating ?? 0) > 0 && (
            <span className="flex items-center gap-0.5 text-amber-400 font-semibold">
              <Star className="w-3 h-3 fill-amber-400" />
              {(movie.douban_rating ?? 0).toFixed(1)}
            </span>
          )}
          {movie.updated_at && (
            <span className="flex items-center gap-0.5">
              <Clock className="w-2.5 h-2.5" />
              {formatDate(movie.updated_at)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function FilmPlaceholder() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.15">
      <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
      <line x1="7" y1="2" x2="7" y2="22" />
      <line x1="17" y1="2" x2="17" y2="22" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <line x1="2" y1="7" x2="7" y2="7" />
      <line x1="2" y1="17" x2="7" y2="17" />
      <line x1="17" y1="7" x2="22" y2="7" />
      <line x1="17" y1="17" x2="22" y2="17" />
    </svg>
  );
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return "-";
  }
}
