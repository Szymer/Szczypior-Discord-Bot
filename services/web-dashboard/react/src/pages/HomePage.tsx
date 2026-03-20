import { Link } from "react-router-dom";
import { asgEvents, getEventTypeLabel } from "@/lib/eventsData";
import { CalendarDays, Target, ChevronRight, Users, MapPin } from "lucide-react";
import { useChallenges } from "@/hooks/useChallenges";

const HomePage = () => {
  const now = new Date().toISOString().split("T")[0];
  const { challenges, isLoading, error } = useChallenges();

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="border border-border bg-card p-6 glow-amber">
        <h1 className="text-2xl font-bold text-primary tracking-widest mb-1">CENTRUM DOWODZENIA</h1>
        <p className="text-tactical text-muted-foreground">// WYZWANIA FITNESS & KALENDARZ ASG</p>
      </div>

      {/* Fitness Challenges */}
      <section className="space-y-4">
        <div className="flex items-center gap-2 border-b border-border pb-3">
          <Target className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-bold text-primary tracking-widest">WYZWANIA FITNESS</h2>
          {isLoading && <span className="text-tactical text-muted-foreground ml-auto animate-pulse">ŁADOWANIE...</span>}
        </div>
        {error && (
          <p className="text-xs text-muted-foreground">{error}</p>
        )}

        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {challenges.map(ch => (
            <Link
              key={ch.id}
              to={`/challenge/${ch.id}`}
              className={`border bg-card p-4 transition-colors hover:border-primary/50 group ${
                ch.isActive ? "border-primary/40 glow-amber" : "border-border"
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{ch.emoji}</span>
                <h3 className="font-bold text-foreground group-hover:text-primary transition-colors">{ch.name}</h3>
                {ch.isActive && (
                  <span className="ml-auto text-tactical bg-primary/20 text-primary px-2 py-0.5">AKTYWNY</span>
                )}
              </div>
              <p className="text-sm text-muted-foreground mb-3">{ch.description}</p>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {ch.startDate.slice(5)} → {ch.endDate.slice(5)}
                </span>
                <span className="text-primary font-bold"></span>
              </div>
              <div className="flex items-center gap-1 mt-2 text-muted-foreground text-tactical group-hover:text-primary transition-colors">
                SZCZEGÓŁY <ChevronRight className="w-3 h-3" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ASG Events Calendar */}
      <section className="space-y-4">
        <div className="flex items-center gap-2 border-b border-border pb-3">
          <CalendarDays className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-bold text-accent tracking-widest">KALENDARZ IMPREZ ASG</h2>
        </div>

        <div className="space-y-3">
          {asgEvents
            .sort((a, b) => a.date.localeCompare(b.date))
            .map(ev => {
              const isPast = ev.date < now;
              return (
                <Link
                  key={ev.id}
                  to={`/event/${ev.id}`}
                  className={`border bg-card p-4 flex items-center gap-4 transition-colors hover:border-accent/50 group ${
                    isPast ? "border-border opacity-60" : "border-border"
                  }`}
                >
                  {/* Date block */}
                  <div className="text-center min-w-[60px] border-r border-border pr-4">
                    <div className="text-2xl font-bold text-foreground">{new Date(ev.date).getDate()}</div>
                    <div className="text-tactical text-muted-foreground">
                      {new Date(ev.date).toLocaleDateString("pl-PL", { month: "short" }).toUpperCase()}
                    </div>
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span>{ev.emoji}</span>
                      <h3 className="font-bold text-foreground group-hover:text-accent transition-colors truncate">
                        {ev.name}
                      </h3>
                      <span className="text-tactical bg-secondary px-2 py-0.5 text-muted-foreground hidden sm:inline">
                        {getEventTypeLabel(ev.type)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{ev.location}</span>
                      <span className="flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        {ev.participants.length}{ev.maxParticipants ? `/${ev.maxParticipants}` : ""}
                      </span>
                    </div>
                  </div>

                  <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-accent transition-colors shrink-0" />
                </Link>
              );
            })}
        </div>
      </section>
    </div>
  );
};

export default HomePage;
