import { currentUser, getChartData, getActivityDistribution, getPlayerActivities, formatPace, formatDuration } from "@/lib/mockData";
import StatCard from "@/components/StatCard";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, PieChart, Pie, Cell } from "recharts";

const COLORS = [
  "hsl(45 100% 50%)",
  "hsl(142 60% 40%)",
  "hsl(200 80% 50%)",
  "hsl(340 70% 50%)",
  "hsl(30 90% 55%)",
  "hsl(270 60% 55%)",
];

const StatsPage = () => {
  const { user } = useAuth();
  if (!user) return null;

  const activities = getPlayerActivities(user.id);
  const chartData = getChartData(user.id);
  const distribution = getActivityDistribution(user.id);

  const last5 = activities.slice(0, 5);
  const avg5Points = last5.length > 0 ? Math.round(last5.reduce((s, a) => s + a.pointsEarned, 0) / last5.length) : 0;
  const bestActivity = activities.reduce((best, a) => a.pointsEarned > best.pointsEarned ? a : best, activities[0]);
  const avgPace = activities.filter(a => a.type.startsWith("running")).length > 0
    ? (activities.filter(a => a.type.startsWith("running")).reduce((s, a) => s + a.paceMinPerKm, 0) / activities.filter(a => a.type.startsWith("running")).length)
    : 0;

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">STATYSTYKI SZCZEGÓŁOWE</h1>
        <p className="text-tactical text-muted-foreground mt-1">// ANALIZA WYNIKÓW — {user.username}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="ŚR. PKT (5 AKT.)" value={avg5Points} variant="primary" />
        <StatCard label="NAJLEPSZA AKT." value={bestActivity?.pointsEarned || 0} sub={bestActivity?.date} variant="accent" />
        <StatCard label="ŚR. TEMPO BIEGU" value={avgPace > 0 ? `${formatPace(avgPace)}/km` : "—"} />
        <StatCard label="CZAS ŁĄCZNY" value={formatDuration(user.totalDurationMin)} />
      </div>

      {/* Points per week */}
      <div className="border border-border bg-card p-4">
        <p className="text-tactical text-muted-foreground mb-4">// PUNKTY TYGODNIOWO</p>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
            <XAxis dataKey="name" tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <YAxis tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "hsl(220 18% 10%)", border: "1px solid hsl(220 15% 18%)", color: "hsl(45 10% 85%)" }} />
            <Bar dataKey="points" fill="hsl(45 100% 50%)" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Distance per week */}
      <div className="border border-border bg-card p-4">
        <p className="text-tactical text-muted-foreground mb-4">// DYSTANS TYGODNIOWO (km)</p>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
            <XAxis dataKey="name" tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <YAxis tick={{ fill: "hsl(220 10% 50%)", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "hsl(220 18% 10%)", border: "1px solid hsl(220 15% 18%)", color: "hsl(45 10% 85%)" }} />
            <Line type="monotone" dataKey="distance" stroke="hsl(142 60% 40%)" strokeWidth={2} dot={{ fill: "hsl(142 60% 40%)" }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Activity distribution */}
      <div className="border border-border bg-card p-4">
        <p className="text-tactical text-muted-foreground mb-4">// ROZKŁAD AKTYWNOŚCI</p>
        <div className="flex flex-col md:flex-row items-center gap-6">
          <ResponsiveContainer width="100%" height={250} className="max-w-[300px]">
            <PieChart>
              <Pie data={distribution} dataKey="count" nameKey="label" cx="50%" cy="50%" outerRadius={90} strokeWidth={1} stroke="hsl(220 18% 10%)">
                {distribution.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "hsl(220 18% 10%)", border: "1px solid hsl(220 15% 18%)", color: "hsl(45 10% 85%)" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex-1 space-y-2 text-sm w-full">
            {distribution.map((d, i) => (
              <div key={d.type} className="flex items-center justify-between border-b border-border pb-1">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />
                  <span>{d.label}</span>
                </div>
                <div className="flex gap-4 text-muted-foreground">
                  <span>{d.count}x</span>
                  <span>{d.distance} km</span>
                  <span className="text-primary font-bold">{d.points.toLocaleString()} pkt</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsPage;
