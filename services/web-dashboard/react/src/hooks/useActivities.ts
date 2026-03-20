import { useState, useEffect } from "react";
import { djangoFetch } from "@/api/djangoClient";
import { type Activity } from "@/lib/mockData";

interface UseActivitiesOptions {
  challengeId?: string | number;
  userId?: string;
  limit?: number;
}

export function useActivities(options: UseActivitiesOptions = {}) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (options.challengeId) params.set("challengeId", String(options.challengeId));
    if (options.userId) params.set("userId", options.userId);
    if (options.limit) params.set("limit", String(options.limit));

    djangoFetch<Activity[]>(`/api/activities/?${params}`)
      .then(setActivities)
      .catch(() => setError("Nie udało się pobrać aktywności"))
      .finally(() => setIsLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.challengeId, options.userId]);

  return { activities, isLoading, error };
}
