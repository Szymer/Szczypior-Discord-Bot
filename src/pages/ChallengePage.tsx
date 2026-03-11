import { useParams, Link } from "react-router-dom";
import { fitnessChallenges } from "@/lib/eventsData";
import { ArrowLeft, Trophy, Calendar, Target } from "lucide-react";

const ChallengePage = () => {
  const { id } = useParams();
  const challenge = fitnessChallenges.find(c => c.id === id);

  if (!challenge) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Wyzwanie nie znalezione.</p>
        <Link to="/home" className="text-primary hover:underline mt-2 inline-block">← Powrót</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Link to="/home" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
        <ArrowLeft className="w-4 h-4" /> POWRÓT
      </Link>

      <div className={`border bg-card p-6 ${challenge.isActive ? "border-primary/40 glow-amber" : "border-border"}`}>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">{challenge.emoji}</span>
          <div>
            <h1 className="text-xl font-bold text-primary tracking-widest">{challenge.name}</h1>
            {challenge.isActive && (
              <span className="text-tactical bg-primary/20 text-primary px-2 py-0.5 inline-block mt-1">AKTYWNE WYZWANIE</span>
            )}
          </div>
        </div>

        <p className="text-foreground mb-6">{challenge.description}</p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
    </div>
  );
};

export default ChallengePage;
