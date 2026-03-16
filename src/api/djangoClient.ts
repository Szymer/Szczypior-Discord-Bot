import { supabase } from "@/auth/supabaseClient";

const DJANGO_API_URL = import.meta.env.VITE_DJANGO_API_URL;

if (!DJANGO_API_URL) {
  throw new Error("Missing VITE_DJANGO_API_URL environment variable");
}

export class DjangoApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "DjangoApiError";
    this.status = status;
  }
}

export interface DjangoUser {
  id: number;
  discord_id: string;
  username: string;
  role: "admin" | "user";
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("No active session");
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function fetchCurrentUser(): Promise<DjangoUser> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${DJANGO_API_URL}/api/auth/me/`, { headers });
  if (!res.ok) throw new DjangoApiError(`Django API error: ${res.status}`, res.status);
  return res.json();
}

export async function djangoFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${DJANGO_API_URL}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  });
  if (!res.ok) throw new DjangoApiError(`Django API error: ${res.status}`, res.status);
  return res.json();
}
