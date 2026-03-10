import { getPlayerActivities, ACTIVITY_CONFIG, formatPace, formatDuration } from "@/lib/mockData";
import { useAuth } from "@/context/AuthContext";

const HistoryPage = () => {
  const { user } = useAuth();
  if (!user) return null;

  const activities = getPlayerActivities(user.id);

  return (
    <div className="space-y-4">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">HISTORIA AKTYWNOŚCI</h1>
        <p className="text-tactical text-muted-foreground mt-1">// REJESTR AKTYWNOŚCI — {user.username} — {activities.length} WPISÓW</p>
      </div>

      <div className="border border-border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="p-3 text-left text-tactical text-muted-foreground">DATA</th>
              <th className="p-3 text-left text-tactical text-muted-foreground">AKTYWNOŚĆ</th>
              <th className="p-3 text-right text-tactical text-muted-foreground">DYSTANS</th>
              <th className="p-3 text-right text-tactical text-muted-foreground">TEMPO</th>
              <th className="p-3 text-right text-tactical text-muted-foreground hidden sm:table-cell">CZAS</th>
              <th className="p-3 text-right text-tactical text-muted-foreground">PUNKTY</th>
              <th className="p-3 text-right text-tactical text-muted-foreground hidden md:table-cell">BONUS</th>
            </tr>
          </thead>
          <tbody>
            {activities.map(a => {
              const cfg = ACTIVITY_CONFIG[a.type];
              return (
                <tr key={a.id} className="border-b border-border hover:bg-secondary/30 transition-colors">
                  <td className="p-3 text-muted-foreground">{a.date}</td>
                  <td className="p-3 font-bold">
                    <span className="mr-1">{cfg.emoji}</span>
                    <span className="hidden sm:inline">{cfg.label}</span>
                  </td>
                  <td className="p-3 text-right">{a.distanceKm} km</td>
                  <td className="p-3 text-right">{formatPace(a.paceMinPerKm)}/km</td>
                  <td className="p-3 text-right hidden sm:table-cell text-muted-foreground">{formatDuration(a.durationMin)}</td>
                  <td className="p-3 text-right font-bold text-primary">{a.pointsEarned.toLocaleString()}</td>
                  <td className="p-3 text-right hidden md:table-cell">
                    {a.bonusPoints > 0 && <span className="text-warning font-bold">+{a.bonusPoints}</span>}
                    {a.elevationGain && <span className="text-muted-foreground text-xs ml-1">↑{a.elevationGain}m</span>}
                    {a.loadKg && <span className="text-muted-foreground text-xs ml-1">{a.loadKg}kg</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default HistoryPage;
