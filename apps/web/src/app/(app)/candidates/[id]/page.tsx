"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { useRequireAuth } from "@/app/providers";
import {
  deleteCandidate,
  getCandidate,
  getDownloadUrl,
  type CandidateDetail,
  type Experience,
} from "@/lib/api";

function month(value: string | null): string {
  return value ? value.slice(0, 7) : "?";
}

function period(item: { date_debut: string | null; date_fin: string | null; is_current: boolean }) {
  const fin = item.is_current ? "présent" : month(item.date_fin);
  return `${month(item.date_debut)} → ${fin}`;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">{title}</h2>
      {children}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex justify-between border-b py-2 text-sm last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="text-right font-medium">{value || "—"}</span>
    </div>
  );
}

export default function CandidateDetailPage() {
  const { user } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!user) return;
    getCandidate(id)
      .then(setCandidate)
      .catch((err) => setError(err instanceof Error ? err.message : "Erreur."))
      .finally(() => setLoading(false));
  }, [user, id]);

  async function download(documentId: string) {
    try {
      const { url } = await getDownloadUrl(documentId);
      window.open(url, "_blank");
    } catch {
      alert("Téléchargement impossible.");
    }
  }

  async function handleDelete() {
    if (!confirm("Supprimer définitivement ce candidat et toutes ses données ?")) return;
    setDeleting(true);
    try {
      await deleteCandidate(id);
      router.push("/candidates");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible.");
      setDeleting(false);
    }
  }

  if (!user) return null;
  const canWrite = user.role === "admin" || user.role === "recruteur";

  return (
    <div className="space-y-4">
      <Link href="/candidates" className="text-sm text-gray-500 hover:text-gray-900">
        ← Retour aux candidats
      </Link>

      {loading && <p className="text-sm text-gray-500">Chargement…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {candidate && (
        <>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">
                {[candidate.prenom, candidate.nom].filter(Boolean).join(" ") || "(Sans nom)"}
              </h1>
              <p className="text-sm text-gray-500">
                {[candidate.poste_actuel, candidate.seniorite].filter(Boolean).join(" · ") ||
                  "Poste non renseigné"}
              </p>
            </div>
            {canWrite && (
              <div className="flex gap-2">
                <Link
                  href={`/candidates/${id}/edit`}
                  className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
                >
                  Modifier
                </Link>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="rounded border border-red-300 px-3 py-1 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  Supprimer
                </button>
              </div>
            )}
          </div>

          <Section title="Coordonnées & profil">
            <Row label="Email" value={candidate.email} />
            <Row label="Téléphone" value={candidate.telephone} />
            <Row label="Ville" value={candidate.ville} />
            <Row label="Secteur" value={candidate.secteur} />
            <Row label="Spécialité" value={candidate.specialite} />
            <Row
              label="Expérience"
              value={candidate.experience_texte ?? `${candidate.annees_experience} an(s)`}
            />
            <Row label="Statut" value={candidate.status} />
          </Section>

          {candidate.skills.length > 0 && (
            <Section title="Compétences">
              <div className="flex flex-wrap gap-2">
                {candidate.skills.map((s) => (
                  <span
                    key={s.id}
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      s.type === "hard" ? "bg-blue-100 text-blue-700" : "bg-green-100 text-green-700"
                    }`}
                  >
                    {s.name}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {candidate.experiences.length > 0 && (
            <Section title="Expériences">
              <ul className="space-y-3">
                {candidate.experiences.map((e: Experience) => (
                  <li key={e.id} className="text-sm">
                    <div className="font-medium">
                      {[e.poste, e.entreprise].filter(Boolean).join(" — ") || "Expérience"}
                    </div>
                    <div className="text-xs text-gray-500">{period(e)}</div>
                    {e.description && <p className="mt-1 text-gray-600">{e.description}</p>}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {candidate.educations.length > 0 && (
            <Section title="Formations">
              <ul className="space-y-2">
                {candidate.educations.map((f) => (
                  <li key={f.id} className="text-sm">
                    <span className="font-medium">{f.diplome || "Formation"}</span>
                    {f.ecole && <span className="text-gray-600"> — {f.ecole}</span>}
                    {f.annee && <span className="text-xs text-gray-500"> ({f.annee})</span>}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {candidate.langues.length > 0 && (
            <Section title="Langues">
              <div className="flex flex-wrap gap-2 text-sm">
                {candidate.langues.map((l) => (
                  <span key={l.id} className="rounded bg-gray-100 px-2 py-0.5">
                    {l.name}
                    {l.level ? ` (${l.level})` : ""}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {candidate.activites_extra.length > 0 && (
            <Section title="Activités extra-professionnelles">
              <ul className="space-y-2">
                {candidate.activites_extra.map((a) => (
                  <li key={a.id} className="text-sm">
                    <span className="font-medium">
                      {[a.titre, a.organisation].filter(Boolean).join(" — ") || "Activité"}
                    </span>
                    <span className="text-xs text-gray-500"> {period(a)}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          <Section title="Documents">
            {candidate.documents.length === 0 ? (
              <p className="text-sm text-gray-500">Aucun document.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {candidate.documents.map((d) => (
                  <li key={d.id} className="flex items-center justify-between">
                    <span>{d.filename}</span>
                    <button
                      type="button"
                      onClick={() => download(d.id)}
                      className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                    >
                      Télécharger
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </>
      )}
    </div>
  );
}
