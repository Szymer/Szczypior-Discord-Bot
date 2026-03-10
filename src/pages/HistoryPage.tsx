import { roundResults } from "@/lib/mockData";
import { useAuth } from "@/context/AuthContext";

const HistoryPage = () => {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className="space-y-4">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">HISTORIA WYNIKÓW</h1>
        <p className="text-tactical text-muted-foreground mt-1">// REJESTR RUND — {user.username}</p>
      </div>

      <div className="border border-border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="p-3 text-left text-tactical text-muted-foreground">RUNDA</th>
              <th className="p-3 text-left text-tactical text-muted-foreground">DATA</th>
              <th className="p-3 text-right text-tactical text-muted-foreground">PUNKTY</th>
              <th className="p-3 text-right text-tactical text-muted-foreground">POZYCJA</th>
            </tr>
          </thead>
          <tbody>
            {roundResults.map(r => (
              <tr key={r.id} className="border-b border-border hover:bg-secondary/30 transition-colors">
                <td className="p-3 font-bold">{r.roundName}</td>
                <td className="p-3 text-muted-foreground">{r.date}</td>
                <td className="p-3 text-right font-bold text-primary">{r.pointsEarned}</td>
                <td className="p-3 text-right">
                  <span className={r.position <= 3 ? "text-warning font-bold" : ""}>
                    #{r.position}
                  </span>
                  <span className="text-muted-foreground">/{r.totalParticipants}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default HistoryPage;
