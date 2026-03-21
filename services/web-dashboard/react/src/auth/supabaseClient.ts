import { createClient } from "@supabase/supabase-js";
import { getAppEnv } from "@/config/runtimeEnv";

const supabaseUrl = getAppEnv("VITE_SUPABASE_URL");
const supabaseKey =
  getAppEnv("VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY") ?? getAppEnv("VITE_SUPABASE_ANON_KEY");

if (!supabaseUrl || !supabaseKey) {
  throw new Error("Missing VITE_SUPABASE_URL or VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY environment variables");
}

export const supabase = createClient(supabaseUrl, supabaseKey);
