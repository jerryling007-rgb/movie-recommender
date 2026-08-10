export interface Movie {
  id: number;
  title: string;
  title_en: string;
  category_id: number;
  category_name: string;
  category_slug: string;
  sub_category: string;
  poster_url: string;
  detail_url: string;
  director: string;
  writers: string;
  cast: string;
  genres: string;
  country: string;
  language: string;
  release_date: string;
  episodes: string;
  runtime: string;
  aka: string;
  summary: string;
  resource_info: string;
  year: number;
  douban_rating?: number;
  source_id: string;
  created_at: string;
  updated_at: string;
  download_links?: DownloadLink[];
}

export interface DownloadLink {
  id: number;
  platform: string;
  url: string;
  access_code: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  url_path: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: T[];
}

export interface Stats {
  total: number;
  by_category: { name: string; slug: string; count: number }[];
  by_year: { year: number; count: number }[];
  last_update: string | null;
  total_links?: number;
}

export interface CrawlStatus {
  running: boolean;
  progress: string;
  started_at: string | null;
  result?: { new: number; updated: number };
  error?: string;
}
