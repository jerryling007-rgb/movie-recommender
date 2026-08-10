const BASE = "/api";

import type { Movie, DownloadLink, Category, PaginatedResponse, Stats, CrawlStatus } from "./types";

async function fetchJSON<T>(url: string, params?: Record<string, string>): Promise<T> {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  const res = await fetch(`${BASE}${url}${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export const api = {
  getCategories: () => fetchJSON<Category[]>("/categories"),

  getMovies: (params?: Record<string, string>) =>
    fetchJSON<PaginatedResponse<Movie>>("/movies", params),

  getMovie: (id: number) =>
    fetchJSON<Movie>(`/movies/${id}`),

  getLinks: (id: number) =>
    fetchJSON<{ movie_id: number; links: DownloadLink[]; cached: boolean }>(`/movies/${id}/links`),

  getRecommendations: (id: number, topK?: number) =>
    fetchJSON<{ source: Movie; recommendations: Movie[] }>(
      `/movies/${id}/recommend`,
      topK ? { top_k: String(topK) } : undefined,
    ),

  searchRecommend: (q: string, topK?: number) =>
    fetchJSON<{ query: string; recommendations: Movie[] }>(
      "/recommend/search",
      { q, ...(topK ? { top_k: String(topK) } : {}) },
    ),

  getStats: () => fetchJSON<Stats>("/stats"),

  getCrawlStatus: () => fetchJSON<CrawlStatus>("/crawl/status"),

  startCrawl: (full?: boolean) =>
    fetchJSON<{ message: string; status: CrawlStatus }>(
      "/crawl/start",
      full ? { full: "true" } : undefined,
    ),
};
