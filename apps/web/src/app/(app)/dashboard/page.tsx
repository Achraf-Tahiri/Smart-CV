"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useRequireAuth } from "@/app/providers";
import { getStats, type Stats } from "@/lib/api";

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, value]) => value));
  return (
    <div className="rounded-lg border bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">{title}</h2>
      {entries.length === 0 ? (
        <p className="text-sm text-gray-400">Aucune donnée.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map(([label, value]) => (
            <li key={label}>
              <div className="flex justify-between text-sm">
                <span className="truncate pr-2">{label}</span>
                <span className="font-medium">{value}</span>
              </div>
              <div className="mt-1 h-1.5 rounded bg-gray-100">
                <div
                  className="h-1.5 rounded bg-gray-700"
                  style={{ width: `${(value / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useRequireAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    getStats()
      .then(setStats)
      .catch((err) => setError(err instanceof Error ? err.message : "Erreur."));
  }, [user]);

  if (!user) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tableau de bord</h1>
        <Link href="/candidates" className="text-sm text-blue-600 hover:underline">
          Voir tous les candidats →
        </Link>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {stats && (
        <>
          <div className="rounded-lg border bg-white p-6">
            <p className="text-sm text-gray-500">Candidats au total</p>
            <p className="text-4xl font-bold">{stats.total}</p>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Breakdown title="Par statut" data={stats.by_status} />
            <Breakdown title="Par séniorité" data={stats.by_seniorite} />
            <Breakdown title="Par secteur" data={stats.by_secteur} />
          </div>
        </>
      )}
    </div>
  );
}
