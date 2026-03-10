// ==================== TYPES ====================

export type ActivityType =
  | "running_terrain"
  | "running_treadmill"
  | "swimming"
  | "cycling"
  | "walking"
  | "other_cardio";

export interface ActivityConfig {
  type: ActivityType;
  label: string;
  emoji: string;
  pointsPerKm: number;
  minDistance: number | null; // km, null = no minimum
  bonuses: string[];
}

export const ACTIVITY_CONFIG: Record<ActivityType, ActivityConfig> = {
  running_terrain: {
    type: "running_terrain",
    label: "Bieganie (Teren)",
    emoji: "🏃",
    pointsPerKm: 1000,
    minDistance: null,
    bonuses: ["obciążenie", "przewyższenia"],
  },
  running_treadmill: {
    type: "running_treadmill",
    label: "Bieganie (Bieżnia)",
    emoji: "🏃‍♂️",
    pointsPerKm: 800,
    minDistance: null,
    bonuses: ["obciążenie"],
  },
  swimming: {
    type: "swimming",
    label: "Pływanie",
    emoji: "🏊",
    pointsPerKm: 4000,
    minDistance: null,
    bonuses: [],
  },
  cycling: {
    type: "cycling",
    label: "Rower/Rolki",
    emoji: "🚴",
    pointsPerKm: 300,
    minDistance: 6,
    bonuses: ["przewyższenia"],
  },
  walking: {
    type: "walking",
    label: "Spacer/Trekking",
    emoji: "🚶",
    pointsPerKm: 200,
    minDistance: 3,
    bonuses: ["obciążenie", "przewyższenia"],
  },
  other_cardio: {
    type: "other_cardio",
    label: "Inne Cardio",
    emoji: "🔫",
    pointsPerKm: 800,
    minDistance: null,
    bonuses: ["obciążenie", "przewyższenia"],
  },
};

export interface Activity {
  id: string;
  userId: string;
  type: ActivityType;
  date: string;
  distanceKm: number;
  durationMin: number;
  paceMinPerKm: number; // min/km
  pointsEarned: number;
  bonusPoints: number;
  elevationGain?: number; // meters
  loadKg?: number;
}

export interface SpecialMission {
  id: string;
  name: string;
  description: string;
  month: string;
  bonusPoints: number;
  requirement: string;
  emoji: string;
}

export interface Player {
  id: string;
  username: string;
  totalPoints: number;
  totalDistanceKm: number;
  totalActivities: number;
  totalDurationMin: number;
  rank: number;
  pointsDiff: number;
  favoriteActivity: ActivityType;
  bestPaceMinPerKm: number;
  // Per-activity distances
  runningKm: number;
  swimmingKm: number;
  cyclingKm: number;
  walkingKm: number;
  otherKm: number;
}

// ==================== SPECIAL MISSIONS ====================

export const specialMissions: SpecialMission[] = [
  {
    id: "sm-dec",
    name: "Rozruch Zimowy",
    description: "Wykonaj dowolną aktywność ciągłą na dystansie min. 5 km",
    month: "Grudzień",
    bonusPoints: 2000,
    requirement: "5 km dowolnej aktywności ciągłej",
    emoji: "❄️",
  },
];

// ==================== MOCK DATA GENERATION ====================

const USERNAMES = [
  "WOLF-01", "EAGLE-07", "VIPER-13", "HAWK-22", "COBRA-05",
  "RAVEN-18", "TITAN-03", "GHOST-11", "STORM-09", "BLADE-15",
  "FURY-20", "SHADOW-06", "APEX-14", "IRON-08", "SPARK-17",
  "NOVA-02", "PULSE-19", "STRIKE-04", "RECON-16", "DELTA-10",
];

const activityTypes: ActivityType[] = [
  "running_terrain", "running_treadmill", "swimming", "cycling", "walking", "other_cardio",
];

function rand(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

function generateActivities(userId: string, count: number): Activity[] {
  const activities: Activity[] = [];
  for (let i = 0; i < count; i++) {
    const type = activityTypes[Math.floor(Math.random() * activityTypes.length)];
    const cfg = ACTIVITY_CONFIG[type];
    let distanceKm: number;
    switch (type) {
      case "swimming": distanceKm = Math.round(rand(0.5, 3) * 10) / 10; break;
      case "cycling": distanceKm = Math.round(rand(6, 60) * 10) / 10; break;
      case "walking": distanceKm = Math.round(rand(3, 15) * 10) / 10; break;
      default: distanceKm = Math.round(rand(2, 15) * 10) / 10;
    }

    const paceMinPerKm = type === "swimming"
      ? Math.round(rand(1.8, 3.5) * 10) / 10
      : type === "cycling"
      ? Math.round(rand(1.5, 3) * 10) / 10
      : Math.round(rand(4.5, 7.5) * 10) / 10;

    const durationMin = Math.round(distanceKm * paceMinPerKm);
    const meetsMin = cfg.minDistance === null || distanceKm >= cfg.minDistance;
    const basePoints = meetsMin ? Math.round(distanceKm * cfg.pointsPerKm) : 0;
    const bonusPoints = meetsMin && cfg.bonuses.length > 0 && Math.random() > 0.6
      ? Math.round(basePoints * 0.15)
      : 0;

    const dayOffset = Math.floor(i * (90 / count));
    const date = new Date(2026, 0, 1);
    date.setDate(date.getDate() + dayOffset);

    activities.push({
      id: `${userId}-a${i}`,
      userId,
      type,
      date: date.toISOString().split("T")[0],
      distanceKm,
      durationMin,
      paceMinPerKm,
      pointsEarned: basePoints + bonusPoints,
      bonusPoints,
      elevationGain: cfg.bonuses.includes("przewyższenia") && Math.random() > 0.5
        ? Math.round(rand(50, 500))
        : undefined,
      loadKg: cfg.bonuses.includes("obciążenie") && Math.random() > 0.7
        ? Math.round(rand(5, 25))
        : undefined,
    });
  }
  return activities.sort((a, b) => b.date.localeCompare(a.date));
}

// Generate all player activities
const allPlayerActivities: Record<string, Activity[]> = {};
USERNAMES.forEach((_, i) => {
  const uid = `p${i + 1}`;
  allPlayerActivities[uid] = generateActivities(uid, Math.floor(rand(15, 40)));
});

function buildPlayer(username: string, index: number): Player {
  const uid = `p${index + 1}`;
  const acts = allPlayerActivities[uid];
  const totalPoints = acts.reduce((s, a) => s + a.pointsEarned, 0);
  const totalDistanceKm = Math.round(acts.reduce((s, a) => s + a.distanceKm, 0) * 10) / 10;
  const totalDurationMin = acts.reduce((s, a) => s + a.durationMin, 0);

  // Per-type distances
  const byType = (types: ActivityType[]) =>
    Math.round(acts.filter(a => types.includes(a.type)).reduce((s, a) => s + a.distanceKm, 0) * 10) / 10;

  // Favorite activity
  const typeCounts: Record<string, number> = {};
  acts.forEach(a => { typeCounts[a.type] = (typeCounts[a.type] || 0) + 1; });
  const favoriteActivity = (Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "running_terrain") as ActivityType;

  // Best pace (running only)
  const runningActs = acts.filter(a => a.type === "running_terrain" || a.type === "running_treadmill");
  const bestPace = runningActs.length > 0
    ? Math.min(...runningActs.map(a => a.paceMinPerKm))
    : 0;

  return {
    id: uid,
    username,
    totalPoints,
    totalDistanceKm,
    totalActivities: acts.length,
    totalDurationMin,
    rank: 0,
    pointsDiff: Math.floor(Math.random() * 3000) - 500,
    favoriteActivity,
    bestPaceMinPerKm: bestPace,
    runningKm: byType(["running_terrain", "running_treadmill"]),
    swimmingKm: byType(["swimming"]),
    cyclingKm: byType(["cycling"]),
    walkingKm: byType(["walking"]),
    otherKm: byType(["other_cardio"]),
  };
}

export const players: Player[] = USERNAMES
  .map((name, i) => buildPlayer(name, i))
  .sort((a, b) => b.totalPoints - a.totalPoints)
  .map((p, i) => ({ ...p, rank: i + 1 }));

export const currentUser = players.find(p => p.username === "COBRA-05")!;

export function getPlayerActivities(userId: string): Activity[] {
  return allPlayerActivities[userId] || [];
}

// Chart data for current user
export function getChartData(userId: string) {
  const acts = getPlayerActivities(userId);
  // Group by week
  const weekMap: Record<string, { points: number; distance: number; count: number }> = {};
  acts.forEach(a => {
    const d = new Date(a.date);
    const weekStart = new Date(d);
    weekStart.setDate(d.getDate() - d.getDay());
    const key = weekStart.toISOString().split("T")[0];
    if (!weekMap[key]) weekMap[key] = { points: 0, distance: 0, count: 0 };
    weekMap[key].points += a.pointsEarned;
    weekMap[key].distance += a.distanceKm;
    weekMap[key].count++;
  });

  return Object.entries(weekMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([week, data]) => ({
      name: week.slice(5), // MM-DD
      points: data.points,
      distance: Math.round(data.distance * 10) / 10,
      activities: data.count,
    }));
}

// Activity type distribution for pie/bar chart
export function getActivityDistribution(userId: string) {
  const acts = getPlayerActivities(userId);
  const dist: Record<ActivityType, { count: number; distance: number; points: number }> = {} as any;
  activityTypes.forEach(t => { dist[t] = { count: 0, distance: 0, points: 0 }; });
  acts.forEach(a => {
    dist[a.type].count++;
    dist[a.type].distance += a.distanceKm;
    dist[a.type].points += a.pointsEarned;
  });
  return activityTypes
    .map(t => ({
      type: t,
      label: ACTIVITY_CONFIG[t].emoji + " " + ACTIVITY_CONFIG[t].label,
      shortLabel: ACTIVITY_CONFIG[t].emoji,
      ...dist[t],
      distance: Math.round(dist[t].distance * 10) / 10,
    }))
    .filter(d => d.count > 0);
}

export function formatPace(paceMinPerKm: number): string {
  const mins = Math.floor(paceMinPerKm);
  const secs = Math.round((paceMinPerKm - mins) * 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function formatDuration(totalMin: number): string {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? `${h}h ${m}min` : `${m}min`;
}
