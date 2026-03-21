import { supabase } from "@/auth/supabaseClient";
import { getAppEnv } from "@/config/runtimeEnv";

const rawDjangoApiUrl = getAppEnv("VITE_DJANGO_API_URL");
const normalizeUrl = (url: string): string => {
  const trimmed = url.trim().replace(/\/$/, "");
  if (trimmed && !/^https?:\/\//i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
};
const DJANGO_API_URL = rawDjangoApiUrl ? normalizeUrl(rawDjangoApiUrl) : undefined;

if (!DJANGO_API_URL) {
  throw new Error("Missing VITE_DJANGO_API_URL environment variable");
}

const buildDjangoApiUrlHint = (): string =>
  "Check VITE_DJANGO_API_URL - it must point to the Django backend service URL, not the frontend URL.";

const parseJsonOrThrow = async <T>(res: Response): Promise<T> => {
  const contentType = res.headers.get("content-type") || "";
  const bodyText = await res.text();

  if (!contentType.includes("application/json")) {
    throw new Error(
      `Expected JSON from Django API, got '${contentType || "unknown"}' from ${res.url}. ${buildDjangoApiUrlHint()}`
    );
  }

  try {
    return JSON.parse(bodyText) as T;
  } catch {
    throw new Error(
      `Invalid JSON response from ${res.url}. ${buildDjangoApiUrlHint()}`
    );
  }
};

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
  return parseJsonOrThrow<DjangoUser>(res);
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
  return parseJsonOrThrow<T>(res);
}
