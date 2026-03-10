import { useAuth } from "@/context/AuthContext";
import { chartData, roundResults } from "@/lib/mockData";
import StatCard from "@/components/StatCard";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from "recharts";

const StatsPage = () => {
  const { user } = useAuth();
  if (!user) return null;

  const last5 = roundResults.slice(0, 5);
  const avg5 = (last5.reduce((s, r) => s + r.pointsEarned, 0) / last5.length).toFixed(1);
  const bestRound = roundResults.reduce((best, r) => r.pointsEarned > best.pointsEarned ? r : best, roundResults[0]);

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">STATYSTYKI SZCZEGÓŁOWE</h1>
        <p className="text-tactical text-muted-foreground mt-1">// ANALIZA WYNIKÓW — {user.username}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="ŚR. PKT (5 RUND)" value={avg5} variant="primary" />
        <StatCard label="NAJLEPSZA RUNDA" value={bestRound.pointsEarned} sub={bestRound.roundName} variant="accent" />
        <StatCard label="ŁĄCZNE RUNDY" value={roundResults.length} />
        <StatCard label="NAJLEPSZA POZ." value={`#${Math.min(...roundResults.map(r => r.position))}`} />
      </div>

      {/* Points chart */}
      <div className="border border-border bg-card p-4">
        <p className="text-tactical text-muted-foreground mb-4">// PUNKTY W KOLEJNYCH RUNDACH</p>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
            <XAxis dataKey="name" tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <YAxis tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "hsl(220 18% 10%)", border: "1px solid hsl(220 15% 18%)", color: "hsl(45 10% 85%)" }}
            />
            <Bar dataKey="points" fill="hsl(45 100% 50%)" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Position chart */}
      <div className="border border-border bg-card p-4">
        <p className="text-tactical text-muted-foreground mb-4">// POZYCJA W KOLEJNYCH RUNDACH</p>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
            <XAxis dataKey="name" tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <YAxis reversed tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "hsl(220 18% 10%)", border: "1px solid hsl(220 15% 18%)", color: "hsl(45 10% 85%)" }}
            />
            <Line type="monotone" dataKey="position" stroke="hsl(142 60% 40%)" strokeWidth={2} dot={{ fill: "hsl(142 60% 40%)" }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default StatsPage;
