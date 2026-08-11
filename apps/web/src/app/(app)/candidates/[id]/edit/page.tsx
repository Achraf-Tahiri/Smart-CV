"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useRequireAuth } from "@/app/providers";
import { CandidateForm } from "@/components/CandidateForm";
import { getCandidate, updateCandidate, type CandidateDetail, type CandidateInput } from "@/lib/api";

export default function EditCandidatePage() {
  const { user } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    getCandidate(id)
      .then(setCandidate)
      .catch((err) => setError(err instanceof Error ? err.message : "Erreur."));
  }, [user, id]);

  if (!user) return null;
  const canWrite = user.role === "admin" || user.role === "recruteur";
  if (!canWrite) return <p className="text-sm text-gray-600">Accès réservé aux recruteurs.</p>;

  async function onSubmit(data: CandidateInput) {
    setBusy(true);
    setError(null);
    try {
      await updateCandidate(id, data);
      router.push(`/candidates/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de la mise à jour.");
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Modifier le candidat</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!candidate ? (
        <p className="text-sm text-gray-500">Chargement…</p>
      ) : (
        <div className="rounded-lg border bg-white p-6">
          <CandidateForm
            initial={candidate}
            onSubmit={onSubmit}
            submitLabel="Enregistrer"
            busy={busy}
          />
        </div>
      )}
    </div>
  );
}
