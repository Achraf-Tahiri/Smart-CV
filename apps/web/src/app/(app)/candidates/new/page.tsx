"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useRequireAuth } from "@/app/providers";
import { CandidateForm } from "@/components/CandidateForm";
import { createCandidate, type CandidateInput } from "@/lib/api";

export default function NewCandidatePage() {
  const { user } = useRequireAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user) return null;
  const canWrite = user.role === "admin" || user.role === "recruteur";
  if (!canWrite) return <p className="text-sm text-gray-600">Accès réservé aux recruteurs.</p>;

  async function onSubmit(data: CandidateInput) {
    setBusy(true);
    setError(null);
    try {
      const created = await createCandidate(data);
      router.push(`/candidates/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de la création.");
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Nouveau candidat</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="rounded-lg border bg-white p-6">
        <CandidateForm onSubmit={onSubmit} submitLabel="Créer" busy={busy} />
      </div>
    </div>
  );
}
