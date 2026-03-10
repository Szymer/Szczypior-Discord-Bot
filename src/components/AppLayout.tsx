import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { BarChart3, Home, LogOut, Medal, ScrollText, Shield } from "lucide-react";

const navItems = [
  { to: "/dashboard", label: "PANEL", icon: Home },
  { to: "/ranking", label: "RANKING", icon: Medal },
  { to: "/stats", label: "STATYSTYKI", icon: BarChart3 },
  { to: "/history", label: "HISTORIA", icon: ScrollText },
];

const AppLayout = ({ children }: { children: React.ReactNode }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top bar */}
      <header className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-primary" />
          <span className="text-primary font-bold tracking-widest text-sm hidden sm:block">SYSTEM RANKINGOWY</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-tactical text-muted-foreground hidden sm:block">
            OPERATOR: <span className="text-foreground">{user?.username}</span>
          </span>
          <span className="text-tactical text-primary">#{user?.rank}</span>
          <button onClick={handleLogout} className="text-muted-foreground hover:text-destructive transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Nav */}
      <nav className="border-b border-border bg-card/50 px-4 flex gap-1 overflow-x-auto">
        {navItems.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className={`flex items-center gap-2 px-4 py-3 text-tactical transition-colors border-b-2 ${
              location.pathname === to
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </Link>
        ))}
      </nav>

      {/* Content */}
      <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full">{children}</main>

      {/* Footer */}
      <footer className="border-t border-border px-4 py-2 text-center">
        <span className="text-tactical text-muted-foreground">SYS v1.0 // KLASYFIKACJA: JAWNE</span>
      </footer>
    </div>
  );
};

export default AppLayout;
