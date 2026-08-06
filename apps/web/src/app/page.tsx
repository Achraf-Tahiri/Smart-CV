"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Health = { status: string; app: string; env: string; version: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-bold">New Smart CV</h1>
      <p className="text-gray-500">Phase 0 — squelette</p>

      <div className="rounded-lg border px-6 py-4 text-center">
        {health ? (
          <p className="text-green-600">
            API : <b>{health.status}</b> — {health.app} v{health.version} ({health.env})
          </p>
        ) : error ? (
          <p className="text-red-600">API injoignable ({API_URL})</p>
        ) : (
          <p className="text-gray-400">Vérification de l&apos;API…</p>
        )}
      </div>
    </main>
  );
}
