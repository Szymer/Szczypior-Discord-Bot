import { useParams, Link } from "react-router-dom";
import { useState } from "react";
import { asgEvents, getEventTypeLabel } from "@/lib/eventsData";
import { players } from "@/lib/mockData";
import { useAuth } from "@/context/AuthContext";
import { ArrowLeft, MapPin, Users, Calendar, User, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

const EventPage = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const event = asgEvents.find(e => e.id === id);
  const [participants, setParticipants] = useState<string[]>(event?.participants || []);

  if (!event) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Impreza nie znaleziona.</p>
        <Link to="/home" className="text-primary hover:underline mt-2 inline-block">← Powrót</Link>
      </div>
    );
  }

  const isJoined = user ? participants.includes(user.id) : false;
  const isFull = event.maxParticipants ? participants.length >= event.maxParticipants : false;
  const isPast = event.date < new Date().toISOString().split("T")[0];

  const handleToggle = () => {
    if (!user) return;
    if (isJoined) {
      setParticipants(prev => prev.filter(pid => pid !== user.id));
    } else if (!isFull) {
      setParticipants(prev => [...prev, user.id]);
    }
  };

  const participantPlayers = participants
    .map(pid => players.find(p => p.id === pid))
    .filter(Boolean);

  return (
    <div className="space-y-6 max-w-2xl">
      <Link to="/home" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
        <ArrowLeft className="w-4 h-4" /> POWRÓT
      </Link>

      {/* Event header */}
      <div className="border border-border bg-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">{event.emoji}</span>
          <div>
            <h1 className="text-xl font-bold text-primary tracking-widest">{event.name}</h1>
            <span className="text-tactical bg-secondary px-2 py-0.5 text-muted-foreground">
              {getEventTypeLabel(event.type)}
            </span>
          </div>
        </div>

        <p className="text-foreground mb-6">{event.description}</p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="border border-border p-3 bg-secondary/30">
            <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-1">
              <Calendar className="w-3 h-3" /> DATA
            </div>
            <p className="text-sm text-foreground font-bold">
              {new Date(event.date).toLocaleDateString("pl-PL", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
            </p>
          </div>
          <div className="border border-border p-3 bg-secondary/30">
            <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-1">
              <MapPin className="w-3 h-3" /> LOKALIZACJA
            </div>
            <p className="text-sm text-foreground font-bold">{event.location}</p>
          </div>
          <div className="border border-border p-3 bg-secondary/30">
            <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-1">
              <User className="w-3 h-3" /> ORGANIZATOR
            </div>
            <p className="text-sm text-foreground font-bold">{event.organizer}</p>
          </div>
        </div>

        {/* RSVP */}
        {!isPast && (
          <div className="border border-border p-4 bg-secondary/20 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm">
                <Users className="w-4 h-4 text-muted-foreground" />
                <span className="text-foreground font-bold">
                  {participants.length}{event.maxParticipants ? ` / ${event.maxParticipants}` : ""} uczestników
                </span>
                {isFull && <span className="text-tactical text-destructive">PEŁNE</span>}
              </div>
            </div>
            <Button
              onClick={handleToggle}
              variant={isJoined ? "destructive" : "default"}
              disabled={!isJoined && isFull}
              className="gap-2"
            >
              {isJoined ? (
                <><XCircle className="w-4 h-4" /> WYPISZ SIĘ</>
              ) : (
                <><CheckCircle className="w-4 h-4" /> ZAPISZ SIĘ</>
              )}
            </Button>
          </div>
        )}

        {isPast && (
          <div className="border border-border p-4 bg-secondary/20 text-center">
            <span className="text-tactical text-muted-foreground">IMPREZA ZAKOŃCZONA</span>
          </div>
        )}
      </div>

      {/* Participants list */}
      <div className="border border-border bg-card">
        <div className="border-b border-border p-4">
          <h2 className="font-bold text-foreground tracking-widest text-sm flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" /> LISTA UCZESTNIKÓW ({participants.length})
          </h2>
        </div>
        {participantPlayers.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground text-sm">Brak zapisanych uczestników</div>
        ) : (
          <div className="divide-y divide-border">
            {participantPlayers.map((p, i) => (
              <div
                key={p!.id}
                className={`flex items-center gap-3 px-4 py-3 ${
                  p!.id === user?.id ? "bg-primary/10 border-l-2 border-l-primary" : ""
                }`}
              >
                <span className="text-tactical text-muted-foreground w-6 text-right">{i + 1}.</span>
                <span className="font-bold text-foreground">{p!.username}</span>
                <span className="text-tactical text-muted-foreground ml-auto">RANK #{p!.rank}</span>
                {p!.id === user?.id && <span className="text-tactical text-primary">TY</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default EventPage;
