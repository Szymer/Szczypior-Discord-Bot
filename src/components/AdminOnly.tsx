import { useAuth } from "@/context/AuthContext";
import { ReactNode } from "react";

const AdminOnly = ({ children, fallback = null }: { children: ReactNode; fallback?: ReactNode }) => {
  const { user } = useAuth();
  if (!user?.isAdmin) return <>{fallback}</>;
  return <>{children}</>;
};

export default AdminOnly;
