"use client";

import { useState, type FormEvent } from "react";

import type { CandidateInput } from "@/lib/api";
import { SECTEURS, SENIORITES, STATUSES } from "@/lib/constants";

interface Props {
  initial?: Partial<CandidateInput>;
  onSubmit: (data: CandidateInput) => void;
  submitLabel: string;
  busy?: boolean;
}

const inputClass = "w-full rounded border px-3 py-2";
const labelClass = "mb-1 block text-sm font-medium";

export function CandidateForm({ initial, onSubmit, submitLabel, busy }: Props) {
  const [form, setForm] = useState<CandidateInput>({
    prenom: initial?.prenom ?? "",
    nom: initial?.nom ?? "",
    email: initial?.email ?? "",
    telephone: initial?.telephone ?? "",
    ville: initial?.ville ?? "",
    poste_actuel: initial?.poste_actuel ?? "",
    secteur: initial?.secteur ?? "",
    specialite: initial?.specialite ?? "",
    annees_experience: initial?.annees_experience ?? 0,
    seniorite: initial?.seniorite ?? "",
    status: initial?.status ?? "success",
  });

  function set<K extends keyof CandidateInput>(key: K, value: CandidateInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div>
        <label className={labelClass}>Prénom</label>
        <input
          className={inputClass}
          value={form.prenom ?? ""}
          onChange={(e) => set("prenom", e.target.value)}
        />
      </div>
      <div>
        <label className={labelClass}>Nom</label>
        <input
          className={inputClass}
          value={form.nom ?? ""}
          onChange={(e) => set("nom", e.target.value)}
        />
      </div>
      <div>
        <label className={labelClass}>Email</label>
        <input
          className={inputClass}
          value={form.email ?? ""}
          onChange={(e) => set("email", e.target.value)}
        />
      </div>
      <div>
        <label className={labelClass}>Téléphone</label>
        <input
          className={inputClass}
          value={form.telephone ?? ""}
          onChange={(e) => set("telephone", e.target.value)}
        />
      </div>
      <div>
        <label className={labelClass}>Ville</label>
        <input
          className={inputClass}
          value={form.ville ?? ""}
          onChange={(e) => set("ville", e.target.value)}
        />
      </div>
      <div>
        <label className={labelClass}>Poste actuel</label>
        <input
          className={inputClass}
          value={form.poste_actuel ?? ""}
          onChange={(e) => set("poste_actuel", e.target.value)}
        />
      </div>
      <div>
        <label className={labelClass}>Secteur</label>
        <select
          className={inputClass}
          value={form.secteur ?? ""}
          onChange={(e) => set("secteur", e.target.value)}
        >
          <option value="">—</option>
          {SECTEURS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelClass}>Spécialité</label>
        <input
          className={inputClass}
          value={form.specialite ?? ""}
          onChange={(e) => set("specialite", e.target.value)}
        />
      </div>
      <div>
        <label className={labelClass}>Années d’expérience</label>
        <input
          type="number"
          min={0}
          step={0.5}
          className={inputClass}
          value={form.annees_experience ?? 0}
          onChange={(e) => set("annees_experience", Number(e.target.value))}
        />
      </div>
      <div>
        <label className={labelClass}>Séniorité</label>
        <select
          className={inputClass}
          value={form.seniorite ?? ""}
          onChange={(e) => set("seniorite", e.target.value)}
        >
          <option value="">—</option>
          {SENIORITES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelClass}>Statut</label>
        <select
          className={inputClass}
          value={form.status ?? "success"}
          onChange={(e) => set("status", e.target.value)}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-gray-900 px-4 py-2 text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {busy ? "Enregistrement…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
