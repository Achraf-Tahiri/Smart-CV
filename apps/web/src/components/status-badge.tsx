import { cn } from "@/lib/utils";

type KnownStatus = "pending" | "processing" | "success" | "manual_review";

const STATUS_MAP: Record<KnownStatus, { label: string; bg: string; dot: string }> = {
  pending: {
    label: "En attente",
    bg: "bg-status-pending text-status-pending-foreground",
    dot: "bg-status-pending-foreground/60",
  },
  processing: {
    label: "En traitement",
    bg: "bg-status-processing text-status-processing-foreground",
    dot: "bg-status-processing-foreground/60",
  },
  success: {
    label: "Traité",
    bg: "bg-status-success text-status-success-foreground",
    dot: "bg-status-success-foreground/60",
  },
  manual_review: {
    label: "À vérifier",
    bg: "bg-status-review text-status-review-foreground",
    dot: "bg-status-review-foreground/60",
  },
};

const FALLBACK = {
  label: "Inconnu",
  bg: "bg-muted text-muted-foreground",
  dot: "bg-muted-foreground/60",
};

export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const meta = STATUS_MAP[status as KnownStatus] ?? FALLBACK;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        meta.bg,
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", meta.dot)} aria-hidden />
      {meta.label}
    </span>
  );
}
