import { useState, useEffect } from "react";
import { djangoFetch } from "@/api/djangoClient";
import { fitnessChallenges, type FitnessChallenge } from "@/lib/eventsData";

export function useChallenges() {
  const [challenges, setChallenges] = useState<FitnessChallenge[]>(fitnessChallenges);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    djangoFetch<FitnessChallenge[]>("/api/challenges/")
      .then((data) => {
        if (data.length > 0) setChallenges(data);
      })
      .catch(() => {
        setError("Nie udało się pobrać wyzwań — wyświetlam dane lokalne");
      })
      .finally(() => setIsLoading(false));
  }, []);

  return { challenges, isLoading, error };
}
