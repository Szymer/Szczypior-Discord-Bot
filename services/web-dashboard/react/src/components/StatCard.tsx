interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  variant?: "default" | "primary" | "accent";
}

const variantStyles = {
  default: "border-border",
  primary: "border-glow glow-amber",
  accent: "border-accent/30 glow-green",
};

const StatCard = ({ label, value, sub, variant = "default" }: StatCardProps) => (
  <div className={`bg-card border p-4 ${variantStyles[variant]}`}>
    <p className="text-tactical text-muted-foreground mb-1">{label}</p>
    <p className="text-2xl md:text-3xl font-bold text-foreground">{value}</p>
    {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
  </div>
);

export default StatCard;
