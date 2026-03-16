import { useState, useMemo } from "react";
import { currentUser, players, ACTIVITY_CONFIG } from "@/lib/mockData";
import { ArrowUpDown, Search } from "lucide-react";

type SortKey = "rank" | "totalPoints" | "totalDistanceKm" | "totalActivities" | "bestPaceMinPerKm";

const RankingPage = () => {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortAsc, setSortAsc] = useState(true);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(key === "rank"); }
  };

  const sorted = useMemo(() => {
    let list = players.filter(p => p.username.toLowerCase().includes(search.toLowerCase()));
    list.sort((a, b) => sortAsc ? (a[sortKey] as number) - (b[sortKey] as number) : (b[sortKey] as number) - (a[sortKey] as number));
    return list;
  }, [search, sortKey, sortAsc]);

  const SortHeader = ({ label, k }: { label: string; k: SortKey }) => (
    <button onClick={() => toggleSort(k)} className="flex items-center gap-1 text-tactical text-muted-foreground hover:text-foreground transition-colors">
      {label} <ArrowUpDown className="w-3 h-3" />
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">TABELA RANKINGOWA</h1>
        <p className="text-tactical text-muted-foreground mt-1">// KLASYFIKACJA GENERALNA — {players.length} OPERATORÓW</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="SZUKAJ OPERATORA..."
          className="w-full sm:w-72 bg-input border border-border pl-10 pr-4 py-2 text-sm font-mono text-foreground focus:outline-none focus:border-primary"
        />
      </div>

      <div className="border border-border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="p-3 text-left"><SortHeader label="#" k="rank" /></th>
              <th className="p-3 text-left text-tactical text-muted-foreground">OPERATOR</th>
              <th className="p-3 text-right"><SortHeader label="PKT" k="totalPoints" /></th>
              <th className="p-3 text-right text-tactical text-muted-foreground hidden sm:table-cell">DIFF</th>
              <th className="p-3 text-right"><SortHeader label="DYSTANS" k="totalDistanceKm" /></th>
              <th className="p-3 text-right"><SortHeader label="AKT." k="totalActivities" /></th>
              <th className="p-3 text-right hidden md:table-cell text-tactical text-muted-foreground">UL. AKT.</th>
              <th className="p-3 text-right hidden lg:table-cell"><SortHeader label="TEMPO" k="bestPaceMinPerKm" /></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(p => {
              const isMe = p.id === user?.id;
              return (
                <tr
                  key={p.id}
                  className={`border-b border-border transition-colors ${
                    isMe ? "bg-primary/10 border-l-2 border-l-primary" : "hover:bg-secondary/30"
                  }`}
                >
                  <td className="p-3 font-bold">{p.rank}</td>
                  <td className={`p-3 font-bold ${isMe ? "text-primary" : ""}`}>
                    {p.username} {isMe && <span className="text-xs text-primary ml-1">◄ TY</span>}
                  </td>
                  <td className="p-3 text-right font-bold text-primary">{p.totalPoints.toLocaleString()}</td>
                  <td className={`p-3 text-right hidden sm:table-cell ${p.pointsDiff > 0 ? "text-success" : p.pointsDiff < 0 ? "text-danger" : "text-muted-foreground"}`}>
                    {p.pointsDiff > 0 ? "+" : ""}{p.pointsDiff}
                  </td>
                  <td className="p-3 text-right">{p.totalDistanceKm} km</td>
                  <td className="p-3 text-right">{p.totalActivities}</td>
                  <td className="p-3 text-right hidden md:table-cell">{ACTIVITY_CONFIG[p.favoriteActivity].emoji}</td>
                  <td className="p-3 text-right hidden lg:table-cell">
                    {p.bestPaceMinPerKm > 0 ? `${Math.floor(p.bestPaceMinPerKm)}:${Math.round((p.bestPaceMinPerKm % 1) * 60).toString().padStart(2, "0")}/km` : "—"}
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

export default RankingPage;
