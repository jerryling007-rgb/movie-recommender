import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { api } from "../api";
import type { Movie } from "../types";

export default function SearchBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Movie[]>([]);
  const [show, setShow] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setShow(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (query.trim().length > 0) {
        api.getMovies({ keyword: query.trim(), page_size: "8" }).then((data) => {
          setResults(data.items);
          setShow(true);
        });
      } else {
        setResults([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (movie: Movie) => {
    navigate(`/movie/${movie.id}`);
    setQuery("");
    setShow(false);
  };

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 premium-input rounded-lg px-3 py-1.5">
        <Search className="w-4 h-4 text-zinc-600 shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setShow(true)}
          placeholder="搜索影片..."
          className="bg-transparent text-sm text-zinc-200 placeholder-zinc-700 flex-1 outline-none"
        />
      </div>

      {show && results.length > 0 && (
        <div className="absolute top-full mt-2 w-full glass-panel rounded-lg overflow-hidden shadow-2xl max-h-96 overflow-y-auto z-50">
          {results.map((movie) => (
            <button
              key={movie.id}
              onClick={() => handleSelect(movie)}
              className="w-full flex items-center gap-3 px-3 py-2 hover:bg-white/5 transition-colors text-left"
            >
              {movie.poster_url ? (
                <img src={movie.poster_url} alt="" className="w-8 h-12 object-cover rounded shrink-0" />
              ) : (
                <div className="w-8 h-12 bg-zinc-900 rounded shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-sm text-zinc-200 truncate">{movie.title}</p>
                <p className="text-xs text-zinc-600">{movie.genres} {movie.year > 0 ? `· ${movie.year}` : ""}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
