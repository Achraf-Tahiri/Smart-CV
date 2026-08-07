"use client";

import Link from "next/link";
import { useState, type ChangeEvent, type FormEvent } from "react";

import { useRequireAuth } from "@/app/providers";
import { processDocument, uploadDocument, type Candidate } from "@/lib/api";

export default function UploadPage() {
  const { user } = useRequireAuth();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [result, setResult] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setResult(null);
    setError(null);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      setStatus("Import du fichier…");
      const uploaded = await uploadDocument(file);
      setStatus(
        uploaded.deduplicated ? "Fichier déjà connu — retraitement…" : "Extraction IA en cours…",
      );
      const candidate = await processDocument(uploaded.document_id);
      setResult(candidate);
      setStatus(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de l'import.");
      setStatus(null);
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <div className="max-w-lg space-y-4">
      <h1 className="text-2xl font-bold">Importer un CV</h1>
      <p className="text-sm text-gray-500">
        Formats acceptés : PDF, Word (.docx) ou image. Le CV est analysé automatiquement.
      </p>

      <form onSubmit={onSubmit} className="space-y-4 rounded-lg border bg-white p-4">
        <input
          type="file"
          accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.tif,.tiff,.webp"
          onChange={onFileChange}
          className="block w-full text-sm"
        />
        <button
          type="submit"
          disabled={!file || busy}
          className="rounded bg-gray-900 px-3 py-2 text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {busy ? "Traitement…" : "Importer et analyser"}
        </button>
      </form>

      {status && <p className="text-sm text-gray-500">{status}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {result && (
        <div className="rounded-lg border bg-white p-4">
          <p className="mb-2 text-sm">
            Traitement terminé — statut : <strong>{result.status}</strong>
          </p>
          <Link href={`/candidates/${result.id}`} className="text-sm text-blue-600 hover:underline">
            Voir la fiche candidat →
          </Link>
        </div>
      )}
    </div>
  );
}
