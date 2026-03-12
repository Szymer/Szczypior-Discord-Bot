import { useState, useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Shield, CalendarDays, Target, ScrollText, Plus, Search, Trash2, Award, Filter } from "lucide-react";
import { asgEvents, fitnessChallenges, getEventTypeLabel, type AsgEvent, type FitnessChallenge } from "@/lib/eventsData";
import { players, getPlayerActivities, ACTIVITY_CONFIG, formatPace, formatDuration, type Activity, type ActivityType } from "@/lib/mockData";

// ─── State stores (mock, in-memory) ───
let eventsStore = [...asgEvents];
let challengesStore = [...fitnessChallenges];
const bonusStore: Record<string, number> = {}; // activityId -> bonus points

const getAllActivities = (): Activity[] => {
  const all: Activity[] = [];
  players.forEach(p => {
    getPlayerActivities(p.id).forEach(a => all.push(a));
  });
  return all.sort((a, b) => b.date.localeCompare(a.date));
};

// ─── Admin Page ───
const AdminPage = () => {
  return (
    <div className="space-y-6">
      <div className="border border-border bg-card p-6 glow-amber">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold text-primary tracking-widest">PANEL ADMINISTRACYJNY</h1>
            <p className="text-tactical text-muted-foreground">// ZARZĄDZANIE SYSTEMEM RANKINGOWYM</p>
          </div>
        </div>
      </div>

      <Tabs defaultValue="activities" className="space-y-4">
        <TabsList className="bg-card border border-border w-full justify-start gap-1 h-auto p-1 flex-wrap">
          <TabsTrigger value="activities" className="text-tactical data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            <ScrollText className="w-3.5 h-3.5 mr-1.5" /> AKTYWNOŚCI
          </TabsTrigger>
          <TabsTrigger value="events" className="text-tactical data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            <CalendarDays className="w-3.5 h-3.5 mr-1.5" /> EVENTY ASG
          </TabsTrigger>
          <TabsTrigger value="challenges" className="text-tactical data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            <Target className="w-3.5 h-3.5 mr-1.5" /> WYZWANIA
          </TabsTrigger>
        </TabsList>

        <TabsContent value="activities"><ActivitiesTab /></TabsContent>
        <TabsContent value="events"><EventsTab /></TabsContent>
        <TabsContent value="challenges"><ChallengesTab /></TabsContent>
      </Tabs>
    </div>
  );
};

// ═══════════════════════════════════════════
// ACTIVITIES TAB — all activities + filters + special mission bonus
// ═══════════════════════════════════════════
const ActivitiesTab = () => {
  const allActivities = useMemo(getAllActivities, []);
  const [filterUser, setFilterUser] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [search, setSearch] = useState("");
  const [bonuses, setBonuses] = useState<Record<string, number>>({ ...bonusStore });
  const [bonusDialog, setBonusDialog] = useState<Activity | null>(null);
  const [bonusAmount, setBonusAmount] = useState("");
  const [bonusNote, setBonusNote] = useState("");

  const filtered = useMemo(() => {
    return allActivities.filter(a => {
      if (filterUser !== "all" && a.userId !== filterUser) return false;
      if (filterType !== "all" && a.type !== filterType) return false;
      if (filterDateFrom && a.date < filterDateFrom) return false;
      if (filterDateTo && a.date > filterDateTo) return false;
      if (search) {
        const player = players.find(p => p.id === a.userId);
        if (!player?.username.toLowerCase().includes(search.toLowerCase())) return false;
      }
      return true;
    });
  }, [allActivities, filterUser, filterType, filterDateFrom, filterDateTo, search]);

  const addBonus = () => {
    if (!bonusDialog || !bonusAmount) return;
    const amount = parseInt(bonusAmount);
    if (isNaN(amount) || amount <= 0) return;
    bonusStore[bonusDialog.id] = amount;
    setBonuses({ ...bonusStore });
    setBonusDialog(null);
    setBonusAmount("");
    setBonusNote("");
  };

  const removeBonus = (activityId: string) => {
    delete bonusStore[activityId];
    setBonuses({ ...bonusStore });
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="border border-border bg-card p-4 space-y-3">
        <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-2">
          <Filter className="w-3.5 h-3.5" /> FILTRY
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Szukaj operatora..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9 bg-secondary border-border"
            />
          </div>
          <Select value={filterUser} onValueChange={setFilterUser}>
            <SelectTrigger className="bg-secondary border-border">
              <SelectValue placeholder="Operator" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Wszyscy</SelectItem>
              {players.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.username}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="bg-secondary border-border">
              <SelectValue placeholder="Typ aktywności" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Wszystkie typy</SelectItem>
              {Object.values(ACTIVITY_CONFIG).map(cfg => (
                <SelectItem key={cfg.type} value={cfg.type}>{cfg.emoji} {cfg.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="date"
            placeholder="Od"
            value={filterDateFrom}
            onChange={e => setFilterDateFrom(e.target.value)}
            className="bg-secondary border-border"
          />
          <Input
            type="date"
            placeholder="Do"
            value={filterDateTo}
            onChange={e => setFilterDateTo(e.target.value)}
            className="bg-secondary border-border"
          />
        </div>
        <div className="text-tactical text-muted-foreground">
          WYNIKI: {filtered.length} / {allActivities.length}
        </div>
      </div>

      {/* Table */}
      <div className="border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-tactical text-primary">DATA</TableHead>
              <TableHead className="text-tactical text-primary">OPERATOR</TableHead>
              <TableHead className="text-tactical text-primary">TYP</TableHead>
              <TableHead className="text-tactical text-primary">DYSTANS</TableHead>
              <TableHead className="text-tactical text-primary">TEMPO</TableHead>
              <TableHead className="text-tactical text-primary">CZAS</TableHead>
              <TableHead className="text-tactical text-primary">PUNKTY</TableHead>
              <TableHead className="text-tactical text-primary">MISJA SP.</TableHead>
              <TableHead className="text-tactical text-primary">AKCJE</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.slice(0, 100).map(a => {
              const player = players.find(p => p.id === a.userId);
              const cfg = ACTIVITY_CONFIG[a.type];
              const bonus = bonuses[a.id];
              return (
                <TableRow key={a.id} className="border-border">
                  <TableCell className="text-sm">{a.date}</TableCell>
                  <TableCell className="font-bold text-sm">{player?.username ?? a.userId}</TableCell>
                  <TableCell className="text-sm">{cfg.emoji} {cfg.label}</TableCell>
                  <TableCell className="text-sm">{a.distanceKm} km</TableCell>
                  <TableCell className="text-sm">{formatPace(a.paceMinPerKm)}/km</TableCell>
                  <TableCell className="text-sm">{formatDuration(a.durationMin)}</TableCell>
                  <TableCell className="text-sm font-bold text-primary">{a.pointsEarned.toLocaleString()}</TableCell>
                  <TableCell>
                    {bonus ? (
                      <div className="flex items-center gap-1">
                        <Badge variant="outline" className="border-accent text-accent text-tactical">
                          <Award className="w-3 h-3 mr-1" /> +{bonus.toLocaleString()}
                        </Badge>
                        <button onClick={() => removeBonus(a.id)} className="text-destructive hover:text-destructive/80">
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-tactical">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-tactical text-accent hover:text-accent hover:bg-accent/10"
                      onClick={() => { setBonusDialog(a); setBonusAmount(""); setBonusNote(""); }}
                    >
                      <Award className="w-3 h-3 mr-1" /> MISJA
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {filtered.length > 100 && (
          <div className="p-3 text-center text-tactical text-muted-foreground border-t border-border">
            WYŚWIETLONO 100 Z {filtered.length} REKORDÓW
          </div>
        )}
      </div>

      {/* Bonus Dialog */}
      <Dialog open={!!bonusDialog} onOpenChange={open => !open && setBonusDialog(null)}>
        <DialogContent className="bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-primary tracking-widest">PRZYZNAJ MISJĘ SPECJALNĄ</DialogTitle>
          </DialogHeader>
          {bonusDialog && (
            <div className="space-y-4">
              <div className="border border-border bg-secondary p-3 space-y-1">
                <div className="text-tactical text-muted-foreground">AKTYWNOŚĆ</div>
                <div className="text-sm">
                  <span className="font-bold">{players.find(p => p.id === bonusDialog.userId)?.username}</span>
                  {" — "}
                  {ACTIVITY_CONFIG[bonusDialog.type].emoji} {ACTIVITY_CONFIG[bonusDialog.type].label}
                  {" — "}{bonusDialog.distanceKm} km
                  {" — "}{bonusDialog.date}
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-tactical text-muted-foreground">BONUS PUNKTOWY</label>
                <Input
                  type="number"
                  placeholder="np. 2000"
                  value={bonusAmount}
                  onChange={e => setBonusAmount(e.target.value)}
                  className="bg-secondary border-border"
                />
              </div>
              <div className="space-y-2">
                <label className="text-tactical text-muted-foreground">NOTATKA (OPCJONALNIE)</label>
                <Input
                  placeholder="np. Misja Rozruch Zimowy"
                  value={bonusNote}
                  onChange={e => setBonusNote(e.target.value)}
                  className="bg-secondary border-border"
                />
              </div>
              <Button onClick={addBonus} className="w-full">
                <Award className="w-4 h-4 mr-2" /> PRZYZNAJ BONUS
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ═══════════════════════════════════════════
// EVENTS TAB — create / delete ASG events
// ═══════════════════════════════════════════
const EventsTab = () => {
  const [events, setEvents] = useState(eventsStore);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", date: "", location: "", description: "", organizer: "",
    maxParticipants: "", type: "milsim" as AsgEvent["type"],
  });

  const typeEmojis: Record<AsgEvent["type"], string> = {
    milsim: "🎖️", cqb: "🏢", woodland: "🌲", scenario: "📜", other: "🔫",
  };

  const createEvent = () => {
    if (!form.name || !form.date) return;
    const newEvent: AsgEvent = {
      id: `ev-${Date.now()}`,
      name: form.name,
      date: form.date,
      location: form.location,
      description: form.description,
      organizer: form.organizer,
      maxParticipants: form.maxParticipants ? parseInt(form.maxParticipants) : null,
      participants: [],
      type: form.type,
      emoji: typeEmojis[form.type],
    };
    eventsStore = [...eventsStore, newEvent];
    setEvents(eventsStore);
    setDialogOpen(false);
    setForm({ name: "", date: "", location: "", description: "", organizer: "", maxParticipants: "", type: "milsim" });
  };

  const deleteEvent = (id: string) => {
    eventsStore = eventsStore.filter(e => e.id !== id);
    setEvents(eventsStore);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-tactical text-muted-foreground">ZAREJESTROWANE EVENTY: {events.length}</span>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="w-4 h-4 mr-2" /> NOWY EVENT</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader>
              <DialogTitle className="text-primary tracking-widest">UTWÓRZ EVENT ASG</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Nazwa eventu" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-secondary border-border" />
              <Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} className="bg-secondary border-border" />
              <Input placeholder="Lokalizacja" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} className="bg-secondary border-border" />
              <Input placeholder="Organizator" value={form.organizer} onChange={e => setForm({ ...form, organizer: e.target.value })} className="bg-secondary border-border" />
              <Select value={form.type} onValueChange={(v: AsgEvent["type"]) => setForm({ ...form, type: v })}>
                <SelectTrigger className="bg-secondary border-border"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="milsim">🎖️ MilSim</SelectItem>
                  <SelectItem value="cqb">🏢 CQB</SelectItem>
                  <SelectItem value="woodland">🌲 Woodland</SelectItem>
                  <SelectItem value="scenario">📜 Scenariuszowa</SelectItem>
                  <SelectItem value="other">🔫 Inne</SelectItem>
                </SelectContent>
              </Select>
              <Input type="number" placeholder="Max uczestników (opcjonalnie)" value={form.maxParticipants} onChange={e => setForm({ ...form, maxParticipants: e.target.value })} className="bg-secondary border-border" />
              <Textarea placeholder="Opis eventu..." value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-secondary border-border min-h-[80px]" />
              <Button onClick={createEvent} className="w-full"><Plus className="w-4 h-4 mr-2" /> UTWÓRZ</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-tactical text-primary">DATA</TableHead>
              <TableHead className="text-tactical text-primary">NAZWA</TableHead>
              <TableHead className="text-tactical text-primary">TYP</TableHead>
              <TableHead className="text-tactical text-primary">LOKALIZACJA</TableHead>
              <TableHead className="text-tactical text-primary">UCZESTNICY</TableHead>
              <TableHead className="text-tactical text-primary">AKCJE</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.sort((a, b) => a.date.localeCompare(b.date)).map(ev => (
              <TableRow key={ev.id} className="border-border">
                <TableCell className="text-sm">{ev.date}</TableCell>
                <TableCell className="text-sm font-bold">{ev.emoji} {ev.name}</TableCell>
                <TableCell className="text-sm">{getEventTypeLabel(ev.type)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{ev.location}</TableCell>
                <TableCell className="text-sm">{ev.participants.length}{ev.maxParticipants ? `/${ev.maxParticipants}` : ""}</TableCell>
                <TableCell>
                  <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => deleteEvent(ev.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════
// CHALLENGES TAB — create / manage fitness challenges
// ═══════════════════════════════════════════
const ChallengesTab = () => {
  const [challenges, setChallenges] = useState(challengesStore);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", description: "", emoji: "💪", startDate: "", endDate: "", goal: "", bonusPoints: "",
  });

  const createChallenge = () => {
    if (!form.name || !form.startDate || !form.endDate) return;
    const now = new Date().toISOString().split("T")[0];
    const newCh: FitnessChallenge = {
      id: `ch-${Date.now()}`,
      name: form.name,
      description: form.description,
      emoji: form.emoji,
      startDate: form.startDate,
      endDate: form.endDate,
      goal: form.goal,
      bonusPoints: parseInt(form.bonusPoints) || 0,
      isActive: form.startDate <= now && form.endDate >= now,
    };
    challengesStore = [...challengesStore, newCh];
    setChallenges(challengesStore);
    setDialogOpen(false);
    setForm({ name: "", description: "", emoji: "💪", startDate: "", endDate: "", goal: "", bonusPoints: "" });
  };

  const deleteChallenge = (id: string) => {
    challengesStore = challengesStore.filter(c => c.id !== id);
    setChallenges(challengesStore);
  };

  const toggleActive = (id: string) => {
    challengesStore = challengesStore.map(c => c.id === id ? { ...c, isActive: !c.isActive } : c);
    setChallenges(challengesStore);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-tactical text-muted-foreground">WYZWANIA: {challenges.length}</span>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="w-4 h-4 mr-2" /> NOWE WYZWANIE</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader>
              <DialogTitle className="text-primary tracking-widest">UTWÓRZ WYZWANIE FITNESS</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="flex gap-3">
                <Input placeholder="Emoji" value={form.emoji} onChange={e => setForm({ ...form, emoji: e.target.value })} className="bg-secondary border-border w-20" />
                <Input placeholder="Nazwa wyzwania" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-secondary border-border flex-1" />
              </div>
              <Textarea placeholder="Opis..." value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-secondary border-border min-h-[60px]" />
              <Input placeholder="Cel (np. 42 km biegania)" value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })} className="bg-secondary border-border" />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-tactical text-muted-foreground mb-1 block">OD</label>
                  <Input type="date" value={form.startDate} onChange={e => setForm({ ...form, startDate: e.target.value })} className="bg-secondary border-border" />
                </div>
                <div>
                  <label className="text-tactical text-muted-foreground mb-1 block">DO</label>
                  <Input type="date" value={form.endDate} onChange={e => setForm({ ...form, endDate: e.target.value })} className="bg-secondary border-border" />
                </div>
              </div>
              <Input type="number" placeholder="Bonus punktowy" value={form.bonusPoints} onChange={e => setForm({ ...form, bonusPoints: e.target.value })} className="bg-secondary border-border" />
              <Button onClick={createChallenge} className="w-full"><Plus className="w-4 h-4 mr-2" /> UTWÓRZ</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-tactical text-primary">NAZWA</TableHead>
              <TableHead className="text-tactical text-primary">OKRES</TableHead>
              <TableHead className="text-tactical text-primary">CEL</TableHead>
              <TableHead className="text-tactical text-primary">BONUS</TableHead>
              <TableHead className="text-tactical text-primary">STATUS</TableHead>
              <TableHead className="text-tactical text-primary">AKCJE</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {challenges.map(ch => (
              <TableRow key={ch.id} className="border-border">
                <TableCell className="text-sm font-bold">{ch.emoji} {ch.name}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{ch.startDate} → {ch.endDate}</TableCell>
                <TableCell className="text-sm">{ch.goal}</TableCell>
                <TableCell className="text-sm text-primary font-bold">+{ch.bonusPoints.toLocaleString()}</TableCell>
                <TableCell>
                  <button onClick={() => toggleActive(ch.id)}>
                    <Badge variant={ch.isActive ? "default" : "secondary"} className="text-tactical cursor-pointer">
                      {ch.isActive ? "AKTYWNE" : "NIEAKTYWNE"}
                    </Badge>
                  </button>
                </TableCell>
                <TableCell>
                  <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => deleteChallenge(ch.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default AdminPage;
