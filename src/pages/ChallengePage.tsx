import { useParams, Link } from "react-router-dom";
import { fitnessChallenges } from "@/lib/eventsData";
import { currentUser, getPlayerActivities, ACTIVITY_CONFIG, formatPace, formatDuration } from "@/lib/mockData";
import StatCard from "@/components/StatCard";
import { ArrowLeft, Trophy, Calendar, Target, ChevronRight, Users } from "lucide-react";

const ChallengeListView = () => {
  const activeChallenges = fitnessChallenges.filter(c => c.isActive);
  const pastChallenges = fitnessChallenges.filter(c => !c.isActive);

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-3">
        <h1 className="text-xl font-bold text-primary tracking-widest">WYZWANIA FITNESS</h1>
        <p className="text-tactical text-muted-foreground mt-1">// WYBIERZ WYZWANIE, ABY ZOBACZYĆ AKTYWNOŚCI UCZESTNIKÓW</p>
      </div>

      {activeChallenges.length > 0 && (
        <div className="space-y-3">
          <p className="text-tactical text-muted-foreground">▸ AKTYWNE WYZWANIA</p>
          {activeChallenges.map(ch => (
            <Link
              key={ch.id}
              to={`/challenge/${ch.id}`}
              className="border border-primary/40 bg-card p-4 flex items-center gap-4 hover:bg-primary/5 transition-colors group glow-amber block"
            >
              <span className="text-3xl">{ch.emoji}</span>
              <div className="flex-1 min-w-0">
                <h3 className="text-foreground font-bold tracking-wide">{ch.name}</h3>
                <p className="text-sm text-muted-foreground mt-1">{ch.description}</p>
                <div className="flex items-center gap-4 mt-2 text-tactical text-muted-foreground">
                  <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {ch.startDate} — {ch.endDate}</span>
                  <span className="flex items-center gap-1"><Trophy className="w-3 h-3 text-primary" /> +{ch.bonusPoints.toLocaleString()} pkt</span>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </Link>
          ))}
        </div>
      )}

      {pastChallenges.length > 0 && (
        <div className="space-y-3">
          <p className="text-tactical text-muted-foreground">▸ ZAKOŃCZONE WYZWANIA</p>
          {pastChallenges.map(ch => (
            <Link
              key={ch.id}
              to={`/challenge/${ch.id}`}
              className="border border-border bg-card p-4 flex items-center gap-4 hover:bg-secondary/50 transition-colors group block"
            >
              <span className="text-3xl opacity-60">{ch.emoji}</span>
              <div className="flex-1 min-w-0">
                <h3 className="text-foreground font-bold tracking-wide">{ch.name}</h3>
                <p className="text-sm text-muted-foreground mt-1">{ch.description}</p>
                <div className="flex items-center gap-4 mt-2 text-tactical text-muted-foreground">
                  <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {ch.startDate} — {ch.endDate}</span>
                  <span className="flex items-center gap-1"><Trophy className="w-3 h-3" /> +{ch.bonusPoints.toLocaleString()} pkt</span>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

const ChallengeDetailView = ({ id }: { id: string }) => {
  const user = currentUser;
  const challenge = fitnessChallenges.find(c => c.id === id);

  if (!challenge) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Wyzwanie nie znalezione.</p>
        <Link to="/challenges" className="text-primary hover:underline mt-2 inline-block">← Powrót</Link>
      </div>
    );
  }

  const allActivities = getPlayerActivities(user.id);
  const challengeActivities = allActivities.filter(
    a => a.date >= challenge.startDate && a.date <= challenge.endDate
  );

  const totalDistance = Math.round(challengeActivities.reduce((s, a) => s + a.distanceKm, 0) * 10) / 10;
  const totalPoints = challengeActivities.reduce((s, a) => s + a.pointsEarned, 0);
  const totalDuration = challengeActivities.reduce((s, a) => s + a.durationMin, 0);
  const activityCount = challengeActivities.length;

  const runningActs = challengeActivities.filter(a => a.type === "running_terrain" || a.type === "running_treadmill");
  const bestPace = runningActs.length > 0 ? Math.min(...runningActs.map(a => a.paceMinPerKm)) : 0;

  const typeCounts: Record<string, { count: number; distance: number; points: number }> = {};
  challengeActivities.forEach(a => {
    if (!typeCounts[a.type]) typeCounts[a.type] = { count: 0, distance: 0, points: 0 };
    typeCounts[a.type].count++;
    typeCounts[a.type].distance += a.distanceKm;
    typeCounts[a.type].points += a.pointsEarned;
  });
  const sortedTypes = Object.entries(typeCounts).sort((a, b) => b[1].points - a[1].points);

  const longestActivity = challengeActivities.length > 0
    ? challengeActivities.reduce((best, a) => a.distanceKm > best.distanceKm ? a : best)
    : null;

  return (
    <div className="space-y-6">
      <Link to="/challenges" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
        <ArrowLeft className="w-4 h-4" /> POWRÓT DO WYZWAŃ
      </Link>

      {/* Challenge header */}
      <div className={`border bg-card p-6 ${challenge.isActive ? "border-primary/40 glow-amber" : "border-border"}`}>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">{challenge.emoji}</span>
          <div>
            <h1 className="text-xl font-bold text-primary tracking-widest">{challenge.name}</h1>
            {challenge.isActive && (
              <span className="text-tactical bg-primary/20 text-primary px-2 py-0.5 inline-block mt-1">AKTYWNE WYZWANIE</span>
            )}
          </div>
        </div>
        <p className="text-muted-foreground text-sm mb-4">{challenge.description}</p>
        <div className="grid grid-cols-3 gap-3">
          <div className="border border-border p-3 bg-secondary/30">
            <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-1">
              <Target className="w-3 h-3" /> CEL
            </div>
            <p className="text-sm text-foreground font-bold">{challenge.goal}</p>
          </div>
          <div className="border border-border p-3 bg-secondary/30">
            <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-1">
              <Calendar className="w-3 h-3" /> OKRES
            </div>
            <p className="text-sm text-foreground font-bold">{challenge.startDate} — {challenge.endDate}</p>
          </div>
          <div className="border border-border p-3 bg-secondary/30">
            <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-1">
              <Trophy className="w-3 h-3" /> NAGRODA
            </div>
            <p className="text-sm text-primary font-bold">+{challenge.bonusPoints.toLocaleString()} pkt</p>
          </div>
        </div>
      </div>

      {/* Operator panel */}
      <div className="border-b border-border pb-3">
        <h2 className="text-lg font-bold text-primary tracking-widest">AKTYWNOŚCI UCZESTNIKÓW — {challenge.name.toUpperCase()}</h2>
        <p className="text-tactical text-muted-foreground mt-1">// DANE {user.username} W OKRESIE WYZWANIA</p>
      </div>

      {challengeActivities.length === 0 ? (
        <div className="border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground text-tactical">// BRAK AKTYWNOŚCI W OKRESIE WYZWANIA</p>
          <p className="text-sm text-muted-foreground mt-2">Okres: {challenge.startDate} — {challenge.endDate}</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatCard label="AKTYWNOŚCI" value={activityCount} sub="W OKRESIE WYZWANIA" variant="primary" />
            <StatCard label="PUNKTY" value={totalPoints.toLocaleString()} sub="ZDOBYTE W WYZWANIU" variant="primary" />
            <StatCard label="DYSTANS" value={`${totalDistance} km`} sub="ŁĄCZNY W WYZWANIU" variant="accent" />
            <StatCard label="CZAS" value={formatDuration(totalDuration)} sub="ŁĄCZNY CZAS" />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatCard label="NAJLEPSZE TEMPO" value={bestPace > 0 ? `${formatPace(bestPace)}/km` : "—"} sub="BIEGANIE" />
            <StatCard label="ŚR. PKT/AKT." value={Math.round(totalPoints / activityCount)} sub="ŚREDNIA" />
            <StatCard label="ŚR. DYSTANS" value={`${(totalDistance / activityCount).toFixed(1)} km`} sub="NA AKTYWNOŚĆ" />
            <StatCard label="NAJDŁUŻSZY" value={longestActivity ? `${longestActivity.distanceKm} km` : "—"} sub={longestActivity ? ACTIVITY_CONFIG[longestActivity.type].label : ""} />
          </div>

          {/* Activity breakdown */}
          <div className="border border-border bg-card p-4">
            <p className="text-tactical text-muted-foreground mb-3">// ROZKŁAD AKTYWNOŚCI W WYZWANIU</p>
            <div className="space-y-2">
              {sortedTypes.map(([type, data]) => {
                const cfg = ACTIVITY_CONFIG[type as keyof typeof ACTIVITY_CONFIG];
                const pct = Math.round((data.points / totalPoints) * 100);
                return (
                  <div key={type} className="flex items-center gap-3">
                    <span className="text-lg w-8">{cfg.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-foreground font-bold">{cfg.label}</span>
                        <span className="text-tactical text-muted-foreground">
                          {data.count}x · {Math.round(data.distance * 10) / 10} km · {data.points.toLocaleString()} pkt
                        </span>
                      </div>
                      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div className="h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Activities list */}
          <div className="border border-border bg-card p-4">
            <p className="text-tactical text-muted-foreground mb-3">// AKTYWNOŚCI W OKRESIE WYZWANIA</p>
            <div className="space-y-2">
              {challengeActivities.slice(0, 10).map(act => (
                <div key={act.id} className="flex items-center gap-4 text-sm border-b border-border/50 pb-2 last:border-0">
                  <span className="text-lg">{ACTIVITY_CONFIG[act.type].emoji}</span>
                  <span className="text-muted-foreground w-20">{act.date}</span>
                  <span className="text-foreground flex-1">{ACTIVITY_CONFIG[act.type].label}</span>
                  <span className="text-foreground font-bold">{act.distanceKm} km</span>
                  <span className="text-muted-foreground">{formatPace(act.paceMinPerKm)}/km</span>
                  <span className="text-primary font-bold">{act.pointsEarned} pkt</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const ChallengePage = () => {
  const { id } = useParams();

  if (!id) return <ChallengeListView />;
  return <ChallengeDetailView id={id} />;
};

export default ChallengePage;
