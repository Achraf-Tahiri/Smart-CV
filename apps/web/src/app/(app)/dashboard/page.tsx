"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertCircle, CheckCircle2, Clock, Users } from "lucide-react";

import { useRequireAuth } from "@/app/providers";
import { getStats, type Stats } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// ── Libellés FR pour les statuts ──────────────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  processing: "En traitement",
  success: "Traité",
  manual_review: "À vérifier",
};

// ── Couleur de barre par statut (token bg-status-*-foreground) ────────────────
const STATUS_BAR_COLOR: Record<string, string> = {
  pending: "bg-status-pending-foreground",
  processing: "bg-status-processing-foreground",
  success: "bg-status-success-foreground",
  manual_review: "bg-status-review-foreground",
};

// ── Carte de répartition avec barres CSS ──────────────────────────────────────
function BreakdownCard({
  title,
  entries,
  barColor = "bg-primary",
  scrollable = false,
}: {
  title: string;
  entries: [string, number][];
  barColor?: string | ((key: string) => string);
  scrollable?: boolean;
}) {
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aucune donnée.</p>
        ) : (
          <ul
            className={
              scrollable
                ? "max-h-64 space-y-3 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
                : "space-y-3"
            }
          >
            {entries.map(([label, value]) => (
              <li key={label}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="truncate pr-2 font-medium">{label}</span>
                  <span className="shrink-0 tabular-nums text-muted-foreground">{value}</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted">
                  <div
                    className={`h-1.5 rounded-full transition-all ${typeof barColor === "function" ? barColor(label) : barColor}`}
                    style={{ width: `${(value / max) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ── KPI : une tuile ───────────────────────────────────────────────────────────
function KpiCard({
  label,
  value,
  icon: Icon,
  accentClass,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  accentClass: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <div className={`flex size-12 shrink-0 items-center justify-center rounded-xl ${accentClass}`}>
          <Icon className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="font-display text-3xl font-bold leading-none">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Squelette de chargement ───────────────────────────────────────────────────
function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* KPI */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardContent className="flex items-center gap-4 p-6">
              <Skeleton className="size-12 rounded-xl" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-7 w-12" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {/* Répartitions */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-3">
              <Skeleton className="h-3 w-24" />
            </CardHeader>
            <CardContent className="space-y-4">
              {[...Array(4)].map((_, j) => (
                <div key={j} className="space-y-1">
                  <div className="flex justify-between">
                    <Skeleton className="h-3 w-28" />
                    <Skeleton className="h-3 w-6" />
                  </div>
                  <Skeleton className="h-1.5 w-full" />
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { user } = useRequireAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    getStats()
      .then(setStats)
      .catch((err) => {
        toast.error(err instanceof Error ? err.message : "Impossible de charger les statistiques.");
      })
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) return null;

  // ── Données dérivées ──────────────────────────────────────────────────────
  const total = stats?.total ?? 0;
  const byStatus = stats?.by_status ?? {};
  const traites = byStatus["success"] ?? 0;
  const aVerifier = byStatus["manual_review"] ?? 0;
  const enCours = (byStatus["processing"] ?? 0) + (byStatus["pending"] ?? 0);

  // Par statut : libellés FR + couleur de barre statut
  const statusEntries: [string, number][] = Object.entries(byStatus)
    .sort((a, b) => b[1] - a[1])
    .map(([key, val]) => [STATUS_LABELS[key] ?? key, val] as [string, number]);
  const statusBarColor = (label: string) => {
    const key = Object.keys(STATUS_LABELS).find((k) => STATUS_LABELS[k] === label);
    return key ? (STATUS_BAR_COLOR[key] ?? "bg-primary") : "bg-primary";
  };

  // Par séniorité : tri décroissant
  const senioriteEntries: [string, number][] = Object.entries(stats?.by_seniorite ?? {}).sort(
    (a, b) => b[1] - a[1],
  );

  // Par secteur : top 8 + « Autres »
  const allSecteur = Object.entries(stats?.by_secteur ?? {}).sort((a, b) => b[1] - a[1]);
  const TOP_N = 8;
  const topSecteur: [string, number][] =
    allSecteur.length <= TOP_N
      ? allSecteur
      : [
          ...allSecteur.slice(0, TOP_N),
          ["Autres", allSecteur.slice(TOP_N).reduce((s, [, v]) => s + v, 0)] as [string, number],
        ];

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Tableau de bord</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Vue d&apos;ensemble du vivier de candidats
          </p>
        </div>
        <Link
          href="/candidates"
          className="text-sm text-muted-foreground transition-colors hover:text-primary"
        >
          Voir tous les candidats →
        </Link>
      </div>

      {/* Chargement */}
      {loading && <DashboardSkeleton />}

      {/* Contenu */}
      {!loading && stats && (
        <>
          {/* KPI */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              label="Candidats au total"
              value={total}
              icon={Users}
              accentClass="bg-primary/10 text-primary"
            />
            <KpiCard
              label="Traités"
              value={traites}
              icon={CheckCircle2}
              accentClass="bg-status-success text-status-success-foreground"
            />
            <KpiCard
              label="À vérifier"
              value={aVerifier}
              icon={AlertCircle}
              accentClass="bg-status-review text-status-review-foreground"
            />
            <KpiCard
              label="En cours"
              value={enCours}
              icon={Clock}
              accentClass="bg-status-processing text-status-processing-foreground"
            />
          </div>

          {/* Répartitions */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <BreakdownCard
              title="Par statut"
              entries={statusEntries}
              barColor={statusBarColor}
            />
            <BreakdownCard
              title="Par séniorité"
              entries={senioriteEntries}
            />
            <BreakdownCard
              title="Par secteur"
              entries={topSecteur}
              scrollable={allSecteur.length > TOP_N}
            />
          </div>
        </>
      )}
    </div>
  );
}
