import { useAuth } from "@/context/AuthContext";
import StatCard from "@/components/StatCard";
import { roundResults } from "@/lib/mockData";

const DashboardPage = () => {
  const { user } = useAuth();
  if (!user) return null;

  const avgPoints = (roundResults.reduce((s, r) => s + r.pointsEarned, 0) / roundResults.length).toFixed(1);
  const lastRound = roundResults[0];

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">PANEL OPERATORA</h1>
        <p className="text-tactical text-muted-foreground mt-1">// STATUS BIEŻĄCY — {user.username}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="POZYCJA" value={`#${user.rank}`} sub="W TABELI GŁÓWNEJ" variant="primary" />
        <StatCard label="PUNKTY" value={user.points} sub={`DIFF: ${user.pointsDiff > 0 ? "+" : ""}${user.pointsDiff}`} variant="primary" />
        <StatCard label="MECZE" value={user.matchesPlayed} sub="ŁĄCZNIE ROZEGRANE" />
        <StatCard label="SKUTECZNOŚĆ" value={`${user.accuracy}%`} sub="WIN RATE" variant="accent" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="ZWYCIĘSTWA" value={user.wins} />
        <StatCard label="PORAŻKI" value={user.losses} />
        <StatCard label="REMISY" value={user.draws} />
        <StatCard label="ŚR. PKT/RUNDA" value={avgPoints} />
      </div>

      {lastRound && (
        <div className="border border-border bg-card p-4">
          <p className="text-tactical text-muted-foreground mb-2">// OSTATNIA RUNDA</p>
          <div className="flex flex-wrap gap-6 text-sm">
            <div><span className="text-muted-foreground">RUNDA:</span> <span className="text-foreground">{lastRound.roundName}</span></div>
            <div><span className="text-muted-foreground">DATA:</span> <span className="text-foreground">{lastRound.date}</span></div>
            <div><span className="text-muted-foreground">PUNKTY:</span> <span className="text-primary font-bold">{lastRound.pointsEarned}</span></div>
            <div><span className="text-muted-foreground">POZYCJA:</span> <span className="text-foreground">#{lastRound.position}/{lastRound.totalParticipants}</span></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
