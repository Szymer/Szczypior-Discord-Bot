import { useAuth } from "@/context/AuthContext";
import StatCard from "@/components/StatCard";
import { getPlayerActivities, ACTIVITY_CONFIG, formatPace, formatDuration } from "@/lib/mockData";

const DashboardPage = () => {
  const { user } = useAuth();
  if (!user) return null;

  const activities = getPlayerActivities(user.id);
  const lastActivity = activities[0];
  const avgPointsPerActivity = activities.length > 0
    ? Math.round(user.totalPoints / activities.length)
    : 0;

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">PANEL OPERATORA</h1>
        <p className="text-tactical text-muted-foreground mt-1">// STATUS BIEŻĄCY — {user.username}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="POZYCJA" value={`#${user.rank}`} sub="W TABELI GŁÓWNEJ" variant="primary" />
        <StatCard label="PUNKTY" value={user.totalPoints.toLocaleString()} sub={`DIFF: ${user.pointsDiff > 0 ? "+" : ""}${user.pointsDiff}`} variant="primary" />
        <StatCard label="AKTYWNOŚCI" value={user.totalActivities} sub="ŁĄCZNIE WYKONANYCH" />
        <StatCard label="DYSTANS" value={`${user.totalDistanceKm} km`} sub="ŁĄCZNY DYSTANS" variant="accent" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="BIEGANIE" value={`${user.runningKm} km`} sub="ŁĄCZNIE" />
        <StatCard label="PŁYWANIE" value={`${user.swimmingKm} km`} sub="ŁĄCZNIE" />
        <StatCard label="ROWER/ROLKI" value={`${user.cyclingKm} km`} sub="ŁĄCZNIE" />
        <StatCard label="SPACER" value={`${user.walkingKm} km`} sub="ŁĄCZNIE" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="CZAS ŁĄCZNY" value={formatDuration(user.totalDurationMin)} />
        <StatCard label="ŚR. PKT/AKT." value={avgPointsPerActivity} />
        <StatCard label="NAJLEPSZE TEMPO" value={user.bestPaceMinPerKm > 0 ? `${formatPace(user.bestPaceMinPerKm)}/km` : "—"} sub="BIEGANIE" />
        <StatCard label="UL. AKTYWNOŚĆ" value={ACTIVITY_CONFIG[user.favoriteActivity].emoji} sub={ACTIVITY_CONFIG[user.favoriteActivity].label} />
      </div>

      {lastActivity && (
        <div className="border border-border bg-card p-4">
          <p className="text-tactical text-muted-foreground mb-2">// OSTATNIA AKTYWNOŚĆ</p>
          <div className="flex flex-wrap gap-6 text-sm">
            <div><span className="text-muted-foreground">TYP:</span> <span className="text-foreground">{ACTIVITY_CONFIG[lastActivity.type].emoji} {ACTIVITY_CONFIG[lastActivity.type].label}</span></div>
            <div><span className="text-muted-foreground">DATA:</span> <span className="text-foreground">{lastActivity.date}</span></div>
            <div><span className="text-muted-foreground">DYSTANS:</span> <span className="text-primary font-bold">{lastActivity.distanceKm} km</span></div>
            <div><span className="text-muted-foreground">TEMPO:</span> <span className="text-foreground">{formatPace(lastActivity.paceMinPerKm)}/km</span></div>
            <div><span className="text-muted-foreground">PUNKTY:</span> <span className="text-primary font-bold">{lastActivity.pointsEarned}</span></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
