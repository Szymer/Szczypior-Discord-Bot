export interface Player {
  id: string;
  username: string;
  points: number;
  wins: number;
  losses: number;
  draws: number;
  matchesPlayed: number;
  accuracy: number;
  rank: number;
  pointsDiff: number;
}

export interface RoundResult {
  id: string;
  roundName: string;
  date: string;
  pointsEarned: number;
  position: number;
  totalParticipants: number;
}

const names = [
  "WOLF-01", "EAGLE-07", "VIPER-13", "HAWK-22", "COBRA-05",
  "RAVEN-18", "TITAN-03", "GHOST-11", "STORM-09", "BLADE-15",
  "FURY-20", "SHADOW-06", "APEX-14", "IRON-08", "SPARK-17",
  "NOVA-02", "PULSE-19", "STRIKE-04", "RECON-16", "DELTA-10"
];

export const players: Player[] = names.map((name, i) => {
  const wins = Math.floor(Math.random() * 15) + 3;
  const losses = Math.floor(Math.random() * 10) + 1;
  const draws = Math.floor(Math.random() * 5);
  const matchesPlayed = wins + losses + draws;
  const points = wins * 3 + draws;
  return {
    id: `p${i + 1}`,
    username: name,
    points,
    wins,
    losses,
    draws,
    matchesPlayed,
    accuracy: Math.round((wins / matchesPlayed) * 100),
    rank: 0,
    pointsDiff: Math.floor(Math.random() * 20) - 5,
  };
}).sort((a, b) => b.points - a.points).map((p, i) => ({ ...p, rank: i + 1 }));

export const currentUser = players[4]; // COBRA-05

export const roundResults: RoundResult[] = Array.from({ length: 12 }, (_, i) => ({
  id: `r${i + 1}`,
  roundName: `RUNDA ${12 - i}`,
  date: new Date(2026, 2, 10 - i * 7).toISOString().split("T")[0],
  pointsEarned: Math.floor(Math.random() * 15) + 1,
  position: Math.floor(Math.random() * 20) + 1,
  totalParticipants: 20,
}));

export const chartData = roundResults.slice().reverse().map(r => ({
  name: r.roundName.replace("RUNDA ", "R"),
  points: r.pointsEarned,
  position: r.position,
}));
