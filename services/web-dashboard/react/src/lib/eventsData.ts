// Mock ASG events and fitness challenges data

export interface AsgEvent {
  id: string;
  name: string;
  date: string; // ISO date
  location: string;
  description: string;
  organizer: string;
  maxParticipants: number | null;
  participants: string[]; // user IDs
  type: "milsim" | "cqb" | "woodland" | "scenario" | "other";
  emoji: string;
}

export interface FitnessChallenge {
  id: string;
  name: string;
  description: string;
  emoji: string;
  startDate: string;
  endDate: string;
  goal: string;
  bonusPoints: number;
  isActive: boolean;
}

export const fitnessChallenges: FitnessChallenge[] = [
  {
    id: "ch-1",
    name: "Rozruch Zimowy",
    description: "Wykonaj dowolną aktywność ciągłą na dystansie min. 5 km",
    emoji: "❄️",
    startDate: "2025-12-01",
    endDate: "2025-12-31",
    goal: "5 km dowolnej aktywności ciągłej",
    bonusPoints: 2000,
    isActive: false,
  },
  {
    id: "ch-2",
    name: "Maratończyk Stycznia",
    description: "Przebiegnij łącznie 42.195 km w ciągu miesiąca",
    emoji: "🏃",
    startDate: "2026-01-01",
    endDate: "2026-01-31",
    goal: "42.195 km biegania łącznie",
    bonusPoints: 5000,
    isActive: false,
  },
  {
    id: "ch-3",
    name: "Żelazna Wola",
    description: "Wykonaj minimum 20 aktywności w ciągu miesiąca",
    emoji: "💪",
    startDate: "2026-02-01",
    endDate: "2026-02-28",
    goal: "20 aktywności w miesiącu",
    bonusPoints: 3000,
    isActive: false,
  },
  {
    id: "ch-4",
    name: "Wiosenny Sprint",
    description: "Osiągnij tempo poniżej 5:00 min/km na dystansie min. 5 km",
    emoji: "⚡",
    startDate: "2026-03-01",
    endDate: "2026-03-31",
    goal: "Tempo < 5:00/km na 5+ km",
    bonusPoints: 4000,
    isActive: true,
  },
  {
    id: "ch-5",
    name: "Wodna Torpeda",
    description: "Przepłyń łącznie 10 km w ciągu miesiąca",
    emoji: "🏊",
    startDate: "2026-04-01",
    endDate: "2026-04-30",
    goal: "10 km pływania łącznie",
    bonusPoints: 6000,
    isActive: false,
  },
];

const EVENT_TYPES: Array<{ type: AsgEvent["type"]; emoji: string }> = [
  { type: "milsim", emoji: "🎖️" },
  { type: "cqb", emoji: "🏢" },
  { type: "woodland", emoji: "🌲" },
  { type: "scenario", emoji: "📜" },
  { type: "other", emoji: "🔫" },
];

export const asgEvents: AsgEvent[] = [
  {
    id: "ev-1",
    name: "Operacja Zimowy Wilk",
    date: "2026-03-15",
    location: "Poligon Drawsko, Zachodniopomorskie",
    description: "Całodniowy MilSim z podziałem na dwie frakcje. Scenariusz obejmuje patrol, rekonesans i szturm na bazę przeciwnika. Wymagany mundur w kamuflażu zimowym.",
    organizer: "Team Alpha PL",
    maxParticipants: 60,
    participants: ["p1", "p2", "p5", "p8", "p11", "p14"],
    type: "milsim",
    emoji: "🎖️",
  },
  {
    id: "ev-2",
    name: "CQB Night Raid",
    date: "2026-03-22",
    location: "Hala CQB Warszawa, Mazowieckie",
    description: "Nocna rozgrywka CQB w zamkniętej hali. Krótkie rundy, szybka akcja. Wymagana latarka taktyczna. Limit FPS: 350.",
    organizer: "Warsaw Airsoft Club",
    maxParticipants: 30,
    participants: ["p3", "p5", "p7", "p12"],
    type: "cqb",
    emoji: "🏢",
  },
  {
    id: "ev-3",
    name: "Leśna Zasadzka",
    date: "2026-04-05",
    location: "Lasy Kozienickie, Mazowieckie",
    description: "Klasyczna woodland z elementami taktyki leśnej. Scenariusz: zabezpieczenie konwoju i obrona punktu kontrolnego.",
    organizer: "Grupa Recon South",
    maxParticipants: 80,
    participants: ["p1", "p4", "p6", "p9", "p10", "p13", "p15", "p17"],
    type: "woodland",
    emoji: "🌲",
  },
  {
    id: "ev-4",
    name: "Operacja Świt",
    date: "2026-04-19",
    location: "Fort VII, Poznań",
    description: "Scenariuszowa gra w historycznym forcie. Dwie strony konfliktu, system respawn, punkty do zdobycia. Całodniowa impreza z przerwą na posiłek.",
    organizer: "Poznań MilSim Group",
    maxParticipants: 100,
    participants: ["p2", "p3", "p5", "p8", "p11", "p16", "p18", "p19", "p20"],
    type: "scenario",
    emoji: "📜",
  },
  {
    id: "ev-5",
    name: "Speed QCB Turniej",
    date: "2026-05-03",
    location: "Arena Taktyczna Kraków",
    description: "Turniej SpeedQB — szybkie rundy 3v3. Eliminacje, półfinały, finał. Nagrody dla najlepszych drużyn.",
    organizer: "SpeedQB Polska",
    maxParticipants: 24,
    participants: ["p1", "p7", "p12"],
    type: "cqb",
    emoji: "🏢",
  },
  {
    id: "ev-6",
    name: "Bitwa o Wzgórze 301",
    date: "2026-05-17",
    location: "Poligon Nowa Dęba, Podkarpackie",
    description: "Duży MilSim na otwartym terenie z użyciem pojazdów. Wymagana rejestracja drużynowa (min. 4 os.).",
    organizer: "MilSim Polska",
    maxParticipants: 150,
    participants: ["p2", "p4", "p6", "p8", "p10", "p11", "p13", "p14", "p15", "p17", "p19"],
    type: "milsim",
    emoji: "🎖️",
  },
];

export function getEventById(id: string): AsgEvent | undefined {
  return asgEvents.find(e => e.id === id);
}

export function getEventTypeLabel(type: AsgEvent["type"]): string {
  const labels: Record<AsgEvent["type"], string> = {
    milsim: "MilSim",
    cqb: "CQB",
    woodland: "Woodland",
    scenario: "Scenariuszowa",
    other: "Inne",
  };
  return labels[type];
}
