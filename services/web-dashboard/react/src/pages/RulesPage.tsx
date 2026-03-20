import { ACTIVITY_CONFIG, specialMissions } from "@/lib/mockData";

const RulesPage = () => {
  const configs = Object.values(ACTIVITY_CONFIG);

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">ZASADY PUNKTACJI</h1>
        <p className="text-tactical text-muted-foreground mt-1">// REGULAMIN OPERACYJNY</p>
      </div>

      {/* Activity scoring table */}
      <div className="border border-border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="p-3 text-left text-tactical text-muted-foreground">AKTYWNOŚĆ</th>
              <th className="p-3 text-right text-tactical text-muted-foreground">PKT/KM</th>
              <th className="p-3 text-right text-tactical text-muted-foreground">MIN. DYSTANS</th>
              <th className="p-3 text-left text-tactical text-muted-foreground">BONUSY</th>
            </tr>
          </thead>
          <tbody>
            {configs.map(cfg => (
              <tr key={cfg.type} className="border-b border-border hover:bg-secondary/30 transition-colors">
                <td className="p-3 font-bold">
                  <span className="mr-2">{cfg.emoji}</span>{cfg.label}
                </td>
                <td className="p-3 text-right font-bold text-primary">{cfg.pointsPerKm.toLocaleString()}</td>
                <td className="p-3 text-right text-muted-foreground">
                  {cfg.minDistance ? `${cfg.minDistance} km` : "BRAK"}
                </td>
                <td className="p-3">
                  {cfg.bonuses.length > 0
                    ? cfg.bonuses.map(b => (
                        <span key={b} className="inline-block bg-secondary text-xs px-2 py-0.5 mr-1 text-muted-foreground">{b}</span>
                      ))
                    : <span className="text-muted-foreground">—</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Special Missions */}
      <div className="border-b border-border pb-3">
        <h2 className="text-lg font-bold text-primary tracking-widest">💥 MISJE SPECJALNE</h2>
        <p className="text-tactical text-muted-foreground mt-1">// RAZ W MIESIĄCU — ZADANIE DODATKOWE</p>
      </div>

      {specialMissions.map(m => (
        <div key={m.id} className="border border-border bg-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{m.emoji}</span>
            <h3 className="font-bold text-foreground">{m.name}</h3>
            <span className="text-tactical text-muted-foreground ml-auto">{m.month}</span>
          </div>
          <p className="text-sm text-muted-foreground mb-2">{m.description}</p>
          <div className="flex gap-4 text-sm">
            <div><span className="text-muted-foreground">WYMÓG:</span> <span className="text-foreground">{m.requirement}</span></div>
            <div><span className="text-muted-foreground">NAGRODA:</span> <span className="text-primary font-bold">+{m.bonusPoints.toLocaleString()} pkt</span></div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default RulesPage;
