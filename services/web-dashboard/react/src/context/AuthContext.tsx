import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { Session } from "@supabase/supabase-js";
import { supabase } from "@/auth/supabaseClient";
import { DjangoApiError, fetchCurrentUser, DjangoUser } from "@/api/djangoClient";
import { getAppEnv } from "@/config/runtimeEnv";

interface AuthUser extends DjangoUser {
  isAdmin: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  session: Session | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  loginWithDiscord: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const getDiscordRedirectUrl = (): string => {
  const configured = getAppEnv("VITE_AUTH_REDIRECT_URL");
  if (configured) {
    return configured;
  }
  return `${window.location.origin}/home`;
};

const mapBackendErrorToUserMessage = (err: unknown): string => {
  if (err instanceof DjangoApiError) {
    return `Backend zwrocil blad HTTP ${err.status}. Sprawdz URL backendu i CORS.`;
  }

  if (err instanceof Error) {
    if (/Failed to fetch/i.test(err.message)) {
      return "Brak polaczenia z backendem. Sprawdz VITE_DJANGO_API_URL i dostepnosc serwisu backend.";
    }

    return `Blad backendu: ${err.message}`;
  }

  return "Tymczasowy blad polaczenia z backendem. Sesja zostala zachowana.";
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDjangoUser = useCallback(async () => {
    try {
      setError(null);
      const djangoUser = await fetchCurrentUser();
      setUser({
        ...djangoUser,
        isAdmin: djangoUser.role === "admin",
      });
    } catch (err) {
      console.error("Failed to fetch Django user:", err);

      if (err instanceof DjangoApiError && (err.status === 401 || err.status === 403)) {
        setError("Sesja wygasla albo konto nie ma dostepu. Zaloguj sie ponownie.");
        setUser(null);
        setSession(null);
        await supabase.auth.signOut();
        return;
      }

      setError(mapBackendErrorToUserMessage(err));
    }
  }, []);

  useEffect(() => {
    // Set up auth state listener BEFORE getting initial session
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, newSession) => {
        setSession(newSession);
        if (newSession) {
          // Defer Django fetch to avoid Supabase deadlock
          setTimeout(() => loadDjangoUser(), 0);
        } else {
          setUser(null);
        }
        setIsLoading(false);
      }
    );

    // Get initial session
    supabase.auth.getSession().then(({ data: { session: initialSession } }) => {
      setSession(initialSession);
      if (initialSession) {
        loadDjangoUser().finally(() => setIsLoading(false));
      } else {
        setIsLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, [loadDjangoUser]);

  const loginWithDiscord = async () => {
    setError(null);
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "discord",
      options: { redirectTo: getDiscordRedirectUrl() },
    });
    if (oauthError) {
      setError(oauthError.message);
    }
  };

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isAuthenticated: !!session && !!user,
        isLoading,
        error,
        loginWithDiscord,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be within AuthProvider");
  return ctx;
};
