import { useState } from "react";
import { Outlet, NavLink } from "react-router-dom";
import { Film, LayoutGrid, BarChart3, Menu, X } from "lucide-react";
import SearchBar from "./SearchBar";

const navItems = [
  { to: "/", label: "首页", icon: Film },
  { to: "/browse", label: "浏览", icon: LayoutGrid },
  { to: "/stats", label: "统计", icon: BarChart3 },
];

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#030303] relative">
      {/* 噪点纹理 */}
      <div className="noise-overlay" />

      {/* 背景氛围光斑 */}
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none z-0 overflow-hidden">
        <div className="hero-orb w-[600px] h-[600px] -top-40 -left-40" style={{ background: "radial-gradient(circle, rgba(245,158,11,1) 0%, transparent 70%)" }} />
        <div className="hero-orb w-[500px] h-[500px] -bottom-32 -right-32" style={{ background: "radial-gradient(circle, rgba(168,85,247,1) 0%, transparent 70%)" }} />
      </div>

      {/* 顶部导航 */}
      <header className="glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <NavLink to="/" className="flex items-center gap-2.5 shrink-0 magnetic-btn group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/15 group-hover:shadow-amber-500/25 transition-shadow">
                <Film className="w-5 h-5 text-black" />
              </div>
              <span className="font-bold text-xl gradient-text tracking-tight">MovieRec</span>
            </NavLink>

            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all nav-indicator ${
                      isActive
                        ? "nav-active"
                        : "text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.04]"
                    }`
                  }
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="hidden md:block w-72">
            <SearchBar />
          </div>

          <button
            className="md:hidden p-2 text-zinc-500 hover:text-zinc-300 transition-colors"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden glass border-t border-white/[0.04] px-4 py-4 space-y-2">
            <div className="mb-3"><SearchBar /></div>
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm ${
                    isActive ? "nav-active" : "text-zinc-500"
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            ))}
          </div>
        )}
      </header>

      <main className="max-w-7xl mx-auto px-4 pb-12 relative z-10">
        <Outlet />
      </main>
    </div>
  );
}
