import { useState, useEffect } from "react";
import { BarChart3, Film, Tv, Play, Loader2, Link2 } from "lucide-react";
import { api } from "../api";
import type { Stats } from "../types";

export default function Stats() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => { api.getStats().then(setStats).catch(() => {}); }, []);

  if (!stats) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-700" />
      </div>
    );
  }

  const maxCategory = Math.max(...(stats.by_category || []).map((c) => c.count), 1);
  const maxYear = Math.max(...(stats.by_year || []).map((y) => y.count), 1);

  return (
    <div className="space-y-8 fade-in-up">
      <h1 className="text-xl font-bold text-zinc-200 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-primary-400" />
        数据统计
      </h1>

      {/* 总览 */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <OverviewCard icon={Film} label="总收录" value={stats.total} />
        {(stats.total_links ?? 0) > 0 && (
          <OverviewCard icon={Link2} label="下载链接" value={stats.total_links!} />
        )}
        {stats.by_category?.map((cat) => {
          const iconMap: Record<string, any> = { movie: Film, tv: Tv, anime: Play };
          return (
            <OverviewCard key={cat.slug} icon={iconMap[cat.slug] || Film} label={cat.name} value={cat.count} />
          );
        })}
      </div>

      {stats.last_update && (
        <p className="text-sm text-zinc-600">
          最后更新: {new Date(stats.last_update).toLocaleString("zh-CN")}
        </p>
      )}

      {/* 分类分布 */}
      <div>
        <h2 className="text-lg font-bold text-zinc-300 mb-4">分类分布</h2>
        <div className="space-y-3">
          {(stats.by_category || []).map((cat) => (
            <div key={cat.slug} className="flex items-center gap-3">
              <span className="text-sm text-zinc-500 w-16">{cat.name}</span>
              <div className="flex-1 h-6 bg-zinc-900/50 rounded-full overflow-hidden border border-white/5">
                <div
                  className="h-full bg-gradient-to-r from-primary-600 to-primary-400 rounded-full transition-all duration-700"
                  style={{ width: `${(cat.count / maxCategory) * 100}%` }}
                />
              </div>
              <span className="text-sm text-zinc-300 w-10 text-right font-mono">{cat.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 年份分布 */}
      {stats.by_year && stats.by_year.length > 0 && (
        <div>
          <h2 className="text-lg font-bold text-zinc-300 mb-4">年份分布 (Top 20)</h2>
          <div className="space-y-2">
            {stats.by_year.map((y) => (
              <div key={y.year} className="flex items-center gap-3">
                <span className="text-sm text-zinc-500 w-16 font-mono">{y.year}</span>
                <div className="flex-1 h-5 bg-zinc-900/50 rounded-full overflow-hidden border border-white/5">
                  <div
                    className="h-full bg-gradient-to-r from-primary-700 to-primary-500 rounded-full transition-all duration-700"
                    style={{ width: `${(y.count / maxYear) * 100}%` }}
                  />
                </div>
                <span className="text-sm text-zinc-300 w-10 text-right font-mono">{y.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function OverviewCard({ icon: Icon, label, value }: { icon: any; label: string; value: number }) {
  return (
    <div className="glass-panel rounded-xl p-4">
      <div className="text-primary-400 mb-2"><Icon className="w-5 h-5" /></div>
      <p className="text-2xl font-bold text-zinc-100">{value}</p>
      <p className="text-sm text-zinc-600">{label}</p>
    </div>
  );
}
