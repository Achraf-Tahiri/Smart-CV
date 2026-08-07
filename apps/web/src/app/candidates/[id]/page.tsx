"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useRequireAuth } from "@/app/providers";
import { getCandidate, type Candidate } from "@/lib/api";

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex justify-between border-b py-2 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-right font-medium">{value || "—"}</span>
    </div>
  );
}

export default function CandidateDetailPage() {
  const { user } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    getCandidate(id)
      .then(setCandidate)
      .catch((err) => setError(err instanceof Error ? err.message : "Erreur."))
      .finally(() => setLoading(false));
  }, [user, id]);

  if (!user) return null;

  return (
    <div className="space-y-4">
      <Link href="/candidates" className="text-sm text-gray-500 hover:text-gray-900">
        ← Retour aux candidats
      </Link>

      {loading && <p className="text-sm text-gray-500">Chargement…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {candidate && (
        <div className="rounded-lg border bg-white p-6">
          <h1 className="text-2xl font-bold">
            {[candidate.prenom, candidate.nom].filter(Boolean).join(" ") || "(Sans nom)"}
          </h1>
          <p className="mb-4 text-sm text-gray-500">
            {candidate.poste_actuel ?? "Poste non renseigné"}
          </p>
          <div>
            <Row label="Email" value={candidate.email} />
            <Row label="Téléphone" value={candidate.telephone} />
            <Row label="Ville" value={candidate.ville} />
            <Row label="Secteur" value={candidate.secteur} />
            <Row label="Spécialité" value={candidate.specialite} />
            <Row
              label="Expérience"
              value={
                candidate.experience_texte ?? `${candidate.annees_experience} an(s)`
              }
            />
            <Row label="Séniorité" value={candidate.seniorite} />
            <Row label="Statut" value={candidate.status} />
            <Row label="Source" value={candidate.source} />
          </div>
        </div>
      )}
    </div>
  );
}
