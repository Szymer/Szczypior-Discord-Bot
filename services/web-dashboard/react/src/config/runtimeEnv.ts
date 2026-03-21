type AppEnvKey =
  | "VITE_DJANGO_API_URL"
  | "VITE_SUPABASE_URL"
  | "VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY"
  | "VITE_SUPABASE_ANON_KEY";

const readRuntimeConfig = (): Partial<ImportMetaEnv> => {
  if (typeof window === "undefined") {
    return {};
  }
  return window.__APP_CONFIG__ ?? {};
};

export const getAppEnv = (key: AppEnvKey): string | undefined => {
  const runtimeValue = readRuntimeConfig()[key];
  if (runtimeValue && runtimeValue.trim().length > 0) {
    return runtimeValue;
  }

  const buildTimeValue = import.meta.env[key];
  if (buildTimeValue && buildTimeValue.trim().length > 0) {
    return buildTimeValue;
  }

  return undefined;
};
