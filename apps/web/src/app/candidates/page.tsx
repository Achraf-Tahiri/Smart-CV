"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useRequireAuth } from "@/app/providers";
import { searchCandidates, type Candidate, type Page } from "@/lib/api";
import { SECTEURS } from "@/lib/constants";

const LIMIT = 10;

function candidateName(c: Candidate): string {
  return [c.prenom, c.nom].filter(Boolean).join(" ") || "(Sans nom)";
}

export default function CandidatesPage() {
  const { user } = useRequireAuth();
  const [q, setQ] = useState("");
  const [secteur, setSecteur] = useState("");
  const [ville, setVille] = useState("");
  const [minExp, setMinExp] = useState("");
  const [data, setData] = useState<Page<Candidate> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(
    async (offset: number) => {
      setLoading(true);
      setError(null);
      try {
        const result = await searchCandidates({
          q: q || undefined,
          secteur: secteur || undefined,
          ville: ville || undefined,
          min_experience: minExp ? Number(minExp) : undefined,
          limit: LIMIT,
          offset,
        });
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de recherche.");
      } finally {
        setLoading(false);
      }
    },
    [q, secteur, ville, minExp],
  );

  useEffect(() => {
    if (user) runSearch(0);
    // Chargement initial une fois connecté.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    runSearch(0);
  }

  if (!user) return null;

  const offset = data?.offset ?? 0;
  const total = data?.total ?? 0;

  const canWrite = user.role === "admin" || user.role === "recruteur";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Candidats</h1>
        {canWrite && (
          <Link
            href="/candidates/new"
            className="rounded bg-gray-900 px-3 py-2 text-sm text-white hover:bg-gray-700"
          >
            + Nouveau candidat
          </Link>
        )}
      </div>

      <form onSubmit={onSubmit} className="grid grid-cols-1 gap-3 rounded-lg border bg-white p-4 sm:grid-cols-5">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Rechercher (poste, compétence, nom…)"
          className="rounded border px-3 py-2 sm:col-span-2"
        />
        <select
          value={secteur}
          onChange={(e) => setSecteur(e.target.value)}
          className="rounded border px-3 py-2"
        >
          <option value="">Tous secteurs</option>
          {SECTEURS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          value={ville}
          onChange={(e) => setVille(e.target.value)}
          placeholder="Ville"
          className="rounded border px-3 py-2"
        />
        <input
          value={minExp}
          onChange={(e) => setMinExp(e.target.value)}
          type="number"
          min={0}
          placeholder="Exp. min (ans)"
          className="rounded border px-3 py-2"
        />
        <button
          type="submit"
          className="rounded bg-gray-900 px-3 py-2 text-white hover:bg-gray-700 sm:col-span-5"
        >
          Rechercher
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {loading && <p className="text-sm text-gray-500">Chargement…</p>}

      {data && !loading && (
        <>
          <p className="text-sm text-gray-500">{total} résultat(s)</p>
          <ul className="space-y-2">
            {data.items.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/candidates/${c.id}`}
                  className="block rounded-lg border bg-white p-4 hover:border-gray-400"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{candidateName(c)}</span>
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {c.seniorite ?? c.status}
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-gray-600">
                    {[c.poste_actuel, c.secteur, c.ville].filter(Boolean).join(" · ") || "—"}
                  </div>
                  {c.experience_texte && (
                    <div className="mt-1 text-xs text-gray-400">{c.experience_texte} d’expérience</div>
                  )}
                </Link>
              </li>
            ))}
          </ul>
          {data.items.length === 0 && (
            <p className="text-sm text-gray-500">Aucun candidat ne correspond.</p>
          )}

          <div className="flex items-center justify-between">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => runSearch(Math.max(0, offset - LIMIT))}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
            >
              ← Précédent
            </button>
            <span className="text-xs text-gray-500">
              {total === 0 ? 0 : offset + 1}–{Math.min(offset + LIMIT, total)} sur {total}
            </span>
            <button
              type="button"
              disabled={offset + LIMIT >= total}
              onClick={() => runSearch(offset + LIMIT)}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
            >
              Suivant →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
