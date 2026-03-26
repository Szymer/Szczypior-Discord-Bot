import { useEffect, useMemo, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Shield, CalendarDays, Target, ScrollText, Plus, Search, Trash2, Pencil, Filter } from "lucide-react";
import { ACTIVITY_CONFIG, formatPace, formatDuration } from "@/lib/mockData";
import { djangoFetch } from "@/api/djangoClient";
import { useChallenges } from "@/hooks/useChallenges";

type PointsRules = {
  weight_bonus: {
    min_weight_kg: number;
    distance_points_multiplier: number;
  };
  elevation_bonus: {
    meters_step: number;
    points_per_step: number;
  };
};

const normalizeBonusName = (value: string): string =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();

const hasBonus = (bonuses: string[], bonusName: string): boolean => {
  const normalizedBonus = normalizeBonusName(bonusName);
  return bonuses.some((item) => normalizeBonusName(item) === normalizedBonus);
};

const toFloatOrDefault = (value: unknown, defaultValue: number): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : defaultValue;
};

const toIntOrDefault = (value: unknown, defaultValue: number): number => {
  const parsed = Number.parseInt(String(value), 10);
  return Number.isFinite(parsed) ? parsed : defaultValue;
};

const normalizePointsRules = (pointsRules: unknown): PointsRules => {
  const baseRules: PointsRules = {
    weight_bonus: {
      min_weight_kg: 5,
      distance_points_multiplier: 1.5,
    },
    elevation_bonus: {
      meters_step: 50,
      points_per_step: 500,
    },
  };

  if (!pointsRules || typeof pointsRules !== "object") {
    return baseRules;
  }

  const raw = pointsRules as {
    weight_bonus?: { min_weight_kg?: unknown; distance_points_multiplier?: unknown };
    elevation_bonus?: { meters_step?: unknown; points_per_step?: unknown };
  };

  return {
    weight_bonus: {
      min_weight_kg: toFloatOrDefault(raw.weight_bonus?.min_weight_kg, baseRules.weight_bonus.min_weight_kg),
      distance_points_multiplier: toFloatOrDefault(
        raw.weight_bonus?.distance_points_multiplier,
        baseRules.weight_bonus.distance_points_multiplier,
      ),
    },
    elevation_bonus: {
      meters_step: toIntOrDefault(raw.elevation_bonus?.meters_step, baseRules.elevation_bonus.meters_step),
      points_per_step: toIntOrDefault(raw.elevation_bonus?.points_per_step, baseRules.elevation_bonus.points_per_step),
    },
  };
};

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
  basePoints: number;
  bonusPoints: number;
  weightBonusPoints: number;
  elevationBonusPoints: number;
  missionBonusPoints: number;
  loadKg: number | null;
  elevationGain: number | null;
  challengeId: number | null;
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

interface SpecialMission {
  id: number;
  name: string;
  emoji: string;
  bonusPoints: number;
  description: string;
}

interface EditForm {
  activityType: ActivityType;
  weightKg: string;
  elevationM: string;
  specialMissionId: string;
}

const ActivitiesTab = () => {
  const { challenges } = useChallenges();
  const [players, setPlayers] = useState<PlayerRow[]>([]);
  const [missions, setMissions] = useState<SpecialMission[]>([]);
  const [activities, setActivities] = useState<AdminActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [filterUser, setFilterUser] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterChallenge, setFilterChallenge] = useState<string>("all");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [search, setSearch] = useState("");

  const [editDialog, setEditDialog] = useState<AdminActivity | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ activityType: "running_terrain", weightKg: "", elevationM: "", specialMissionId: "" });

  const loadPlayers = async () => {
    const data = await djangoFetch<PlayerRow[]>("/api/players/");
    setPlayers(data);
  };

  const loadMissions = async () => {
    try {
      const data = await djangoFetch<SpecialMission[]>("/api/admin/missions/");
      setMissions(data);
    } catch (err) {
      console.error("[loadMissions] failed:", err);
    }
  };

  const loadActivities = async () => {
    setIsLoading(true);
    const params = new URLSearchParams();
    params.set("limit", "200");
    if (filterUser !== "all") params.set("userId", filterUser);
    if (filterType !== "all") params.set("type", filterType);
    if (filterChallenge !== "all") params.set("challengeId", filterChallenge);
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
    loadMissions();
  }, []);

  useEffect(() => {
    loadActivities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterUser, filterType, filterChallenge, filterDateFrom, filterDateTo, search]);

  const openEditDialog = (a: AdminActivity) => {
    setEditDialog(a);
    // Try to find matching mission by its bonus_points value (best-effort pre-select)
    const matchedMission = a.missionBonusPoints > 0
      ? missions.find(m => m.bonusPoints === a.missionBonusPoints)
      : undefined;
    setEditForm({
      activityType: a.type,
      weightKg: a.loadKg != null ? String(a.loadKg) : "",
      elevationM: a.elevationGain != null ? String(a.elevationGain) : "",
      specialMissionId: matchedMission ? String(matchedMission.id) : "",
    });
  };

  const saveEdit = async () => {
    if (!editDialog) return;
    await djangoFetch(`/api/admin/activities/${editDialog.id}/`, {
      method: "PATCH",
      body: JSON.stringify({
        activityType: editForm.activityType,
        weightKg: editForm.weightKg !== "" ? parseFloat(editForm.weightKg) : null,
        elevationM: editForm.elevationM !== "" ? parseInt(editForm.elevationM, 10) : null,
        specialMissionId: editForm.specialMissionId !== "" ? editForm.specialMissionId : "",
      }),
    });
    setEditDialog(null);
    await loadActivities();
  };

  // Live preview – mirrors backend formula
  const editPreview = useMemo(() => {
    if (!editDialog) return null;
    const cfg = ACTIVITY_CONFIG[editForm.activityType];
    const dist = editDialog.distanceKm;
    const wKg = editForm.weightKg !== "" ? Number.parseFloat(editForm.weightKg) : null;
    const elM = editForm.elevationM !== "" ? Number.parseInt(editForm.elevationM, 10) : null;
    const challenge = editDialog.challengeId != null
      ? challenges.find((item) => String(item.id) === String(editDialog.challengeId))
      : undefined;
    const pointsRules = normalizePointsRules(challenge?.pointsRules);

    let basePts = Math.trunc(dist * cfg.pointsPerKm);
    let weightBonus = 0;
    if (
      wKg !== null
      && wKg >= pointsRules.weight_bonus.min_weight_kg
      && hasBonus(cfg.bonuses, "obciazenie")
      && pointsRules.weight_bonus.distance_points_multiplier > 1
    ) {
      weightBonus = Math.trunc(basePts * (pointsRules.weight_bonus.distance_points_multiplier - 1));
    }

    let elevationBonus = 0;
    if (
      elM !== null
      && elM > 0
      && hasBonus(cfg.bonuses, "przewyzszenie")
      && pointsRules.elevation_bonus.meters_step > 0
    ) {
      elevationBonus =
        Math.trunc(elM / pointsRules.elevation_bonus.meters_step) * pointsRules.elevation_bonus.points_per_step;
    }

    const selectedMission = editForm.specialMissionId
      ? missions.find(m => String(m.id) === editForm.specialMissionId)
      : undefined;
    const missionBonus = selectedMission ? selectedMission.bonusPoints : 0;

    let totalWithoutMission = basePts + weightBonus + elevationBonus;
    if (totalWithoutMission < 1) {
      basePts = 1;
      totalWithoutMission = 1;
    }

    return {
      basePts,
      weightBonus,
      elevationBonus,
      missionBonus,
      selectedMission,
      total: totalWithoutMission + missionBonus,
    };
  }, [challenges, editDialog, editForm, missions]);

  const visibleActivities = useMemo(() => activities.slice(0, 100), [activities]);

  return (
    <div className="space-y-4">
      <div className="border border-border bg-card p-4 space-y-3">
        <div className="flex items-center gap-2 text-tactical text-muted-foreground mb-2">
          <Filter className="w-3.5 h-3.5" /> FILTRY
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
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
          <Select value={filterChallenge} onValueChange={setFilterChallenge}>
            <SelectTrigger className="bg-secondary border-border"><SelectValue placeholder="Wyzwanie" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Wszystkie wyzwania</SelectItem>
              {challenges.map(ch => <SelectItem key={ch.id} value={String(ch.id)}>{ch.emoji} {ch.name}</SelectItem>)}
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
              <TableHead className="text-tactical text-primary">WYZWANIE</TableHead>
              <TableHead className="text-tactical text-primary">AKCJE</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleActivities.map(a => {
              const player = players.find(p => p.id === a.userId);
              const cfg = ACTIVITY_CONFIG[a.type];
              const challenge = a.challengeId != null ? challenges.find(ch => String(ch.id) === String(a.challengeId)) : null;
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
                  <TableCell className="text-sm">
                    {challenge
                      ? <span className="text-accent">{challenge.emoji} {challenge.name}</span>
                      : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost" className="text-tactical text-accent hover:text-accent hover:bg-accent/10" onClick={() => openEditDialog(a)}>
                      <Pencil className="w-3 h-3 mr-1" /> EDYTUJ
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Dialog open={!!editDialog} onOpenChange={open => !open && setEditDialog(null)}>
        <DialogContent className="bg-card border-border max-w-lg" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="text-primary tracking-widest">EDYTUJ AKTYWNOŚĆ</DialogTitle>
            <DialogDescription className="sr-only">Formularz edycji aktywności — zmień typ, obciążenie, przewyższenie lub misję specjalną.</DialogDescription>
          </DialogHeader>
          {editDialog && editPreview && (() => {
            const cfg = ACTIVITY_CONFIG[editForm.activityType];
            const showWeight = cfg.bonuses.includes("obciążenie");
            const showElevation = cfg.bonuses.includes("przewyższenia");
            return (
              <div className="space-y-4">
                <div className="text-tactical text-muted-foreground text-xs">
                  {editDialog.date} · {editDialog.distanceKm} km
                </div>

                <div className="space-y-1">
                  <label className="text-tactical text-xs text-muted-foreground">TYP AKTYWNOŚCI</label>
                  <Select value={editForm.activityType} onValueChange={(v: ActivityType) => setEditForm({ ...editForm, activityType: v })}>
                    <SelectTrigger className="bg-secondary border-border"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.values(ACTIVITY_CONFIG).map(c => (
                        <SelectItem key={c.type} value={c.type}>{c.emoji} {c.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {showWeight && (
                  <div className="space-y-1">
                    <label className="text-tactical text-xs text-muted-foreground">OBCIĄŻENIE [kg]</label>
                    <Input
                      type="number" min="0" step="0.5"
                      placeholder="np. 10"
                      value={editForm.weightKg}
                      onChange={e => setEditForm({ ...editForm, weightKg: e.target.value })}
                      className="bg-secondary border-border"
                    />
                  </div>
                )}

                {showElevation && (
                  <div className="space-y-1">
                    <label className="text-tactical text-xs text-muted-foreground">PRZEWYŻSZENIE [m]</label>
                    <Input
                      type="number" min="0"
                      placeholder="np. 250"
                      value={editForm.elevationM}
                      onChange={e => setEditForm({ ...editForm, elevationM: e.target.value })}
                      className="bg-secondary border-border"
                    />
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-tactical text-xs text-muted-foreground">MISJA SPECJALNA</label>
                  <Select
                    value={editForm.specialMissionId}
                    onValueChange={v => setEditForm({ ...editForm, specialMissionId: v === "none" ? "" : v })}
                  >
                    <SelectTrigger className="bg-secondary border-border"><SelectValue placeholder="Brak misji" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">— Brak misji</SelectItem>
                      {missions.map(m => (
                        <SelectItem key={m.id} value={String(m.id)}>
                          {m.emoji} {m.name} <span className="text-muted-foreground ml-1">(+{m.bonusPoints.toLocaleString()} pkt)</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {missions.length === 0 && (
                    <p className="text-xs text-muted-foreground">Brak aktywnych misji w bazie danych</p>
                  )}
                </div>

                <div className="border border-border bg-secondary/50 p-3 rounded space-y-1 text-sm">
                  <div className="text-tactical text-xs text-muted-foreground mb-2">PODGLĄD PRZELICZENIA</div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Bazowe</span><span className="font-mono">{editPreview.basePts.toLocaleString()}</span></div>
                  {showWeight && <div className="flex justify-between"><span className="text-muted-foreground">Bonus obciążenie</span><span className="font-mono text-accent">+{editPreview.weightBonus.toLocaleString()}</span></div>}
                  {showElevation && <div className="flex justify-between"><span className="text-muted-foreground">Bonus przewyższenie</span><span className="font-mono text-accent">+{editPreview.elevationBonus.toLocaleString()}</span></div>}
                  <div className="flex justify-between"><span className="text-muted-foreground">Bonus misja</span><span className="font-mono text-accent">+{editPreview.missionBonus.toLocaleString()}</span></div>
                  <div className="flex justify-between border-t border-border pt-1 mt-1"><span className="font-bold text-primary">SUMA</span><span className="font-bold text-primary font-mono">{editPreview.total.toLocaleString()}</span></div>
                </div>

                <Button onClick={saveEdit} className="w-full"><Pencil className="w-4 h-4 mr-2" /> ZAPISZ ZMIANY</Button>
              </div>
            );
          })()}
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
