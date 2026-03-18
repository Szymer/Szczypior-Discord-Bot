import { useEffect, useMemo, useState } from "react";
import { ACTIVITY_CONFIG } from "@/lib/mockData";
import { djangoFetch } from "@/api/djangoClient";
import { useAuth } from "@/context/AuthContext";
import { ArrowUpDown, Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useChallenges } from "@/hooks/useChallenges";

type SortKey = "rank" | "totalPoints" | "totalDistanceKm" | "totalActivities" | "bestPaceMinPerKm";

interface RankingPlayer {
  id: string;
  username: string;
  rank: number;
  totalPoints: number;
  pointsDiff: number;
  totalDistanceKm: number;
  totalActivities: number;
  favoriteActivity: keyof typeof ACTIVITY_CONFIG;
  bestPaceMinPerKm: number | null;
}

const RankingPage = () => {
  const { user } = useAuth();
  const { challenges } = useChallenges();
  const [searchParams, setSearchParams] = useSearchParams();
  const [players, setPlayers] = useState<RankingPlayer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortAsc, setSortAsc] = useState(true);

  const challengeId = searchParams.get("challengeId") ?? "";
  const selectedChallenge = challenges.find(c => String(c.id) === challengeId) ?? null;

  useEffect(() => {
    if (challengeId || challenges.length === 0) return;

    const activeChallenge = challenges.find(c => c.isActive);
    if (!activeChallenge) return;
    if (!/^\d+$/.test(String(activeChallenge.id))) return;

    const next = new URLSearchParams(searchParams);
    next.set("challengeId", String(activeChallenge.id));
    setSearchParams(next, { replace: true });
  }, [challengeId, challenges, searchParams, setSearchParams]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (challengeId && /^\d+$/.test(challengeId)) params.set("challengeId", challengeId);
    const suffix = params.toString() ? `?${params.toString()}` : "";

    setIsLoading(true);
    setError(null);
    djangoFetch<RankingPlayer[]>(`/api/ranking/${suffix}`)
      .then(setPlayers)
      .catch(() => setError("Nie udało się pobrać rankingu"))
      .finally(() => setIsLoading(false));
  }, [challengeId]);

  const handleChallengeChange = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set("challengeId", value);
    else next.delete("challengeId");
    setSearchParams(next);
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(key === "rank"); }
  };

  const sorted = useMemo(() => {
    let list = players.filter(p => p.username.toLowerCase().includes(search.toLowerCase()));
    list.sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return list;
  }, [players, search, sortKey, sortAsc]);

  const SortHeader = ({ label, k }: { label: string; k: SortKey }) => (
    <button onClick={() => toggleSort(k)} className="flex items-center gap-1 text-tactical text-muted-foreground hover:text-foreground transition-colors">
      {label} <ArrowUpDown className="w-3 h-3" />
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">TABELA RANKINGOWA</h1>
        <p className="text-tactical text-muted-foreground mt-1">
          // {selectedChallenge ? `KLASYFIKACJA WYZWANIA: ${selectedChallenge.name.toUpperCase()}` : "KLASYFIKACJA GENERALNA"} — {players.length} OPERATORÓW
        </p>
        {isLoading && <p className="text-tactical text-muted-foreground mt-1 animate-pulse">// ŁADOWANIE...</p>}
        {error && <p className="text-sm text-destructive mt-1">{error}</p>}
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
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

        <select
          value={challengeId}
          onChange={(e) => handleChallengeChange(e.target.value)}
          className="w-full sm:w-96 bg-input border border-border px-3 py-2 text-sm font-mono text-foreground focus:outline-none focus:border-primary"
        >
          <option value="">WSZYSTKIE WYZWANIA</option>
          {challenges.map((challenge) => (
            <option key={challenge.id} value={String(challenge.id)}>
              {challenge.emoji} {challenge.name}
            </option>
          ))}
        </select>
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
              const isMe = p.id === user?.discord_id;
              const favorite = ACTIVITY_CONFIG[p.favoriteActivity] ?? ACTIVITY_CONFIG.other_cardio;
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
                  <td className="p-3 text-right hidden md:table-cell">{favorite.emoji}</td>
                  <td className="p-3 text-right hidden lg:table-cell">
                    {p.bestPaceMinPerKm && p.bestPaceMinPerKm > 0 ? `${Math.floor(p.bestPaceMinPerKm)}:${Math.round((p.bestPaceMinPerKm % 1) * 60).toString().padStart(2, "0")}/km` : "—"}
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
