import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { Shield } from "lucide-react";

const LoginPage = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (login(username, password)) {
      navigate("/dashboard");
    } else {
      setError("BŁĄD AUTORYZACJI — NIEPRAWIDŁOWE DANE");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <Shield className="w-12 h-12 text-primary mb-4" />
          <h1 className="text-2xl font-bold text-primary tracking-widest">SYSTEM RANKINGOWY</h1>
          <p className="text-tactical text-muted-foreground mt-2">PANEL AUTORYZACJI</p>
        </div>

        <form onSubmit={handleSubmit} className="border border-border bg-card p-6 space-y-4 glow-amber">
          <div className="border-b border-border pb-2 mb-4">
            <span className="text-tactical text-muted-foreground">// WPROWADŹ DANE LOGOWANIA</span>
          </div>

          {error && (
            <div className="bg-destructive/10 border border-destructive/30 p-3 text-destructive text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="text-tactical text-muted-foreground block mb-1">IDENTYFIKATOR</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-input border border-border p-3 text-foreground font-mono focus:outline-none focus:border-primary transition-colors"
              placeholder="CALL_SIGN"
              required
            />
          </div>

          <div>
            <label className="text-tactical text-muted-foreground block mb-1">HASŁO</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-input border border-border p-3 text-foreground font-mono focus:outline-none focus:border-primary transition-colors"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-primary text-primary-foreground font-bold py-3 tracking-widest hover:opacity-90 transition-opacity"
          >
            ZALOGUJ
          </button>

          <p className="text-center text-muted-foreground text-xs mt-4">
            DEMO: wpisz dowolny login i hasło
          </p>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
