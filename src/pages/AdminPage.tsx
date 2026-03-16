import { useEffect, useMemo, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Shield, CalendarDays, Target, ScrollText, Plus, Search, Trash2, Award, Filter } from "lucide-react";
import { ACTIVITY_CONFIG, formatPace, formatDuration } from "@/lib/mockData";
import { djangoFetch } from "@/api/djangoClient";

type ActivityType = keyof typeof ACTIVITY_CONFIG;

interface PlayerRow {
  id: string;
  username: string;
}

interface AdminActivity {
  id: string;
  userId: string;
  type: ActivityType;
  date: string;
  distanceKm: number;
  durationMin: number;
  paceMinPerKm: number | null;
  pointsEarned: number;
  bonusPoints: number;
}

interface AdminEvent {
  id: number;
  name: string;
  date: string;
  location: string;
  description: string;
  organizer: string;
  maxParticipants: number | null;
  participants: string[];
  type: "milsim" | "cqb" | "woodland" | "scenario" | "other";
  emoji: string;
}

interface AdminChallenge {
  id: number;
  name: string;
  description: string;
  emoji: string;
  startDate: string;
  endDate: string;
  goal: string;
  bonusPoints: number;
  isActive: boolean;
}

const getEventTypeLabel = (type: AdminEvent["type"]) => {
  const labels: Record<AdminEvent["type"], string> = {
    milsim: "MilSim",
    cqb: "CQB",
    woodland: "Woodland",
    scenario: "Scenariuszowa",
    other: "Inne",
  };
  return labels[type];
};

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

const ActivitiesTab = () => {
  const [players, setPlayers] = useState<PlayerRow[]>([]);
  const [activities, setActivities] = useState<AdminActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [filterUser, setFilterUser] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [search, setSearch] = useState("");

  const [bonusDialog, setBonusDialog] = useState<AdminActivity | null>(null);
  const [bonusAmount, setBonusAmount] = useState("");

  const loadPlayers = async () => {
    const data = await djangoFetch<PlayerRow[]>("/api/players/");
    setPlayers(data);
  };

  const loadActivities = async () => {
    setIsLoading(true);
    const params = new URLSearchParams();
    params.set("limit", "200");
    if (filterUser !== "all") params.set("userId", filterUser);
    if (filterType !== "all") params.set("type", filterType);
    if (filterDateFrom) params.set("dateFrom", filterDateFrom);
    if (filterDateTo) params.set("dateTo", filterDateTo);
    if (search.trim()) params.set("search", search.trim());

    try {
      const data = await djangoFetch<AdminActivity[]>(`/api/admin/activities/?${params.toString()}`);
      setActivities(data);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPlayers();
  }, []);

  useEffect(() => {
    loadActivities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterUser, filterType, filterDateFrom, filterDateTo, search]);

  const addBonus = async () => {
    if (!bonusDialog || !bonusAmount) return;
    const points = parseInt(bonusAmount, 10);
    if (isNaN(points) || points <= 0) return;

    await djangoFetch(`/api/admin/activities/${bonusDialog.id}/bonus/`, {
      method: "POST",
      body: JSON.stringify({ points }),
    });

    setBonusDialog(null);
    setBonusAmount("");
    await loadActivities();
  };

  const visibleActivities = useMemo(() => activities.slice(0, 100), [activities]);

  return (
    <div className="space-y-4">
      <div className="border border-border bg-card p-4 space-y-3">
        <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-2">
          <Filter className="w-3.5 h-3.5" /> FILTRY
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Szukaj operatora..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9 bg-secondary border-border" />
          </div>
          <Select value={filterUser} onValueChange={setFilterUser}>
            <SelectTrigger className="bg-secondary border-border"><SelectValue placeholder="Operator" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Wszyscy</SelectItem>
              {players.map(p => <SelectItem key={p.id} value={p.id}>{p.username}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="bg-secondary border-border"><SelectValue placeholder="Typ aktywności" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Wszystkie typy</SelectItem>
              {Object.values(ACTIVITY_CONFIG).map(cfg => <SelectItem key={cfg.type} value={cfg.type}>{cfg.emoji} {cfg.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Input type="date" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)} className="bg-secondary border-border" />
          <Input type="date" value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)} className="bg-secondary border-border" />
        </div>
        <div className="text-tactical text-muted-foreground">WYNIKI: {activities.length}{isLoading ? " (ładowanie...)" : ""}</div>
      </div>

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
              <TableHead className="text-tactical text-primary">BONUS</TableHead>
              <TableHead className="text-tactical text-primary">AKCJE</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleActivities.map(a => {
              const player = players.find(p => p.id === a.userId);
              const cfg = ACTIVITY_CONFIG[a.type];
              return (
                <TableRow key={a.id} className="border-border">
                  <TableCell className="text-sm">{a.date}</TableCell>
                  <TableCell className="font-bold text-sm">{player?.username ?? a.userId}</TableCell>
                  <TableCell className="text-sm">{cfg.emoji} {cfg.label}</TableCell>
                  <TableCell className="text-sm">{a.distanceKm} km</TableCell>
                  <TableCell className="text-sm">{a.paceMinPerKm ? `${formatPace(a.paceMinPerKm)}/km` : "—"}</TableCell>
                  <TableCell className="text-sm">{formatDuration(a.durationMin ?? 0)}</TableCell>
                  <TableCell className="text-sm font-bold text-primary">{a.pointsEarned.toLocaleString()}</TableCell>
                  <TableCell className="text-sm">{a.bonusPoints ? `+${a.bonusPoints}` : "—"}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost" className="text-tactical text-accent hover:text-accent hover:bg-accent/10" onClick={() => { setBonusDialog(a); setBonusAmount(""); }}>
                      <Award className="w-3 h-3 mr-1" /> MISJA
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Dialog open={!!bonusDialog} onOpenChange={open => !open && setBonusDialog(null)}>
        <DialogContent className="bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-primary tracking-widest">PRZYZNAJ BONUS</DialogTitle>
          </DialogHeader>
          {bonusDialog && (
            <div className="space-y-4">
              <Input type="number" placeholder="np. 2000" value={bonusAmount} onChange={e => setBonusAmount(e.target.value)} className="bg-secondary border-border" />
              <Button onClick={addBonus} className="w-full"><Award className="w-4 h-4 mr-2" /> PRZYZNAJ BONUS</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const EventsTab = () => {
  const [events, setEvents] = useState<AdminEvent[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", date: "", location: "", description: "", organizer: "", type: "milsim" as AdminEvent["type"],
  });

  const loadEvents = async () => {
    const data = await djangoFetch<AdminEvent[]>("/api/admin/events/");
    setEvents(data);
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const createEvent = async () => {
    if (!form.name || !form.date) return;
    await djangoFetch("/api/admin/events/", {
      method: "POST",
      body: JSON.stringify({ ...form }),
    });
    setDialogOpen(false);
    setForm({ name: "", date: "", location: "", description: "", organizer: "", type: "milsim" });
    await loadEvents();
  };

  const deleteEvent = async (id: number) => {
    await djangoFetch(`/api/admin/events/${id}/`, { method: "DELETE" });
    await loadEvents();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-tactical text-muted-foreground">ZAREJESTROWANE EVENTY: {events.length}</span>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild><Button><Plus className="w-4 h-4 mr-2" /> NOWY EVENT</Button></DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="text-primary tracking-widest">UTWÓRZ EVENT ASG</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Nazwa eventu" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-secondary border-border" />
              <Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} className="bg-secondary border-border" />
              <Input placeholder="Lokalizacja" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} className="bg-secondary border-border" />
              <Input placeholder="Organizator" value={form.organizer} onChange={e => setForm({ ...form, organizer: e.target.value })} className="bg-secondary border-border" />
              <Select value={form.type} onValueChange={(v: AdminEvent["type"]) => setForm({ ...form, type: v })}>
                <SelectTrigger className="bg-secondary border-border"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="milsim">🎖️ MilSim</SelectItem>
                  <SelectItem value="cqb">🏢 CQB</SelectItem>
                  <SelectItem value="woodland">🌲 Woodland</SelectItem>
                  <SelectItem value="scenario">📜 Scenariuszowa</SelectItem>
                  <SelectItem value="other">🔫 Inne</SelectItem>
                </SelectContent>
              </Select>
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
            {[...events].sort((a, b) => a.date.localeCompare(b.date)).map(ev => (
              <TableRow key={ev.id} className="border-border">
                <TableCell className="text-sm">{ev.date}</TableCell>
                <TableCell className="text-sm font-bold">{ev.emoji} {ev.name}</TableCell>
                <TableCell className="text-sm">{getEventTypeLabel(ev.type)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{ev.location}</TableCell>
                <TableCell className="text-sm">{ev.participants.length}</TableCell>
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

const ChallengesTab = () => {
  const [challenges, setChallenges] = useState<AdminChallenge[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", emoji: "💪", startDate: "", endDate: "", goal: "", bonusPoints: "" });

  const loadChallenges = async () => {
    const data = await djangoFetch<AdminChallenge[]>("/api/admin/challenges/");
    setChallenges(data);
  };

  useEffect(() => {
    loadChallenges();
  }, []);

  const createChallenge = async () => {
    if (!form.name || !form.startDate || !form.endDate) return;
    await djangoFetch("/api/admin/challenges/", {
      method: "POST",
      body: JSON.stringify({ ...form, bonusPoints: parseInt(form.bonusPoints || "0", 10), isActive: false }),
    });
    setDialogOpen(false);
    setForm({ name: "", description: "", emoji: "💪", startDate: "", endDate: "", goal: "", bonusPoints: "" });
    await loadChallenges();
  };

  const deleteChallenge = async (id: number) => {
    await djangoFetch(`/api/admin/challenges/${id}/`, { method: "DELETE" });
    await loadChallenges();
  };

  const toggleActive = async (ch: AdminChallenge) => {
    await djangoFetch(`/api/admin/challenges/${ch.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ isActive: !ch.isActive }),
    });
    await loadChallenges();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-tactical text-muted-foreground">WYZWANIA: {challenges.length}</span>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild><Button><Plus className="w-4 h-4 mr-2" /> NOWE WYZWANIE</Button></DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="text-primary tracking-widest">UTWÓRZ WYZWANIE FITNESS</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div className="flex gap-3">
                <Input placeholder="Emoji" value={form.emoji} onChange={e => setForm({ ...form, emoji: e.target.value })} className="bg-secondary border-border w-20" />
                <Input placeholder="Nazwa wyzwania" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-secondary border-border flex-1" />
              </div>
              <Textarea placeholder="Opis..." value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-secondary border-border min-h-[60px]" />
              <Input placeholder="Cel" value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })} className="bg-secondary border-border" />
              <div className="grid grid-cols-2 gap-3">
                <Input type="date" value={form.startDate} onChange={e => setForm({ ...form, startDate: e.target.value })} className="bg-secondary border-border" />
                <Input type="date" value={form.endDate} onChange={e => setForm({ ...form, endDate: e.target.value })} className="bg-secondary border-border" />
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
                  <button onClick={() => toggleActive(ch)}>
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
