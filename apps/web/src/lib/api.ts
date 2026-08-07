// Client API typé pour l'API New Smart CV.
// Gère le jeton JWT (localStorage) et l'en-tête Authorization.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

const TOKEN_KEY = "nscv_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

// --- Types (miroir des schémas Pydantic de l'API) ---

export type Role = "admin" | "recruteur" | "lecteur";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Candidate {
  id: string;
  prenom: string | null;
  nom: string | null;
  email: string | null;
  telephone: string | null;
  ville: string | null;
  poste_actuel: string | null;
  secteur: string | null;
  specialite: string | null;
  annees_experience: number;
  experience_texte: string | null;
  seniorite: string | null;
  status: string;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface Experience {
  id: string;
  poste: string | null;
  entreprise: string | null;
  date_debut: string | null;
  date_fin: string | null;
  is_current: boolean;
  description: string | null;
}

export interface Education {
  id: string;
  diplome: string | null;
  ecole: string | null;
  annee: number | null;
  description: string | null;
}

export interface Activity {
  id: string;
  titre: string | null;
  organisation: string | null;
  date_debut: string | null;
  date_fin: string | null;
  is_current: boolean;
  description: string | null;
}

export interface Skill {
  id: string;
  name: string;
  type: "hard" | "soft";
}

export interface Language {
  id: string;
  name: string;
  level: string | null;
}

export interface DocumentRef {
  id: string;
  filename: string;
  content_type: string | null;
  source: string;
  created_at: string;
}

export interface CandidateDetail extends Candidate {
  experiences: Experience[];
  educations: Education[];
  activites_extra: Activity[];
  skills: Skill[];
  langues: Language[];
  documents: DocumentRef[];
}

export interface Stats {
  total: number;
  by_status: Record<string, number>;
  by_secteur: Record<string, number>;
  by_seniorite: Record<string, number>;
}

// Champs modifiables (création / édition manuelle).
export interface CandidateInput {
  prenom?: string | null;
  nom?: string | null;
  email?: string | null;
  telephone?: string | null;
  ville?: string | null;
  poste_actuel?: string | null;
  secteur?: string | null;
  specialite?: string | null;
  annees_experience?: number;
  seniorite?: string | null;
  status?: string;
}

export interface Page<T> {
  total: number;
  items: T[];
  limit: number;
  offset: number;
}

export interface UploadResult {
  candidate_id: string;
  document_id: string;
  filename: string;
  file_hash: string;
  deduplicated: boolean;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    throw new ApiError(401, "Session expirée, reconnecte-toi.");
  }
  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* corps non JSON */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// --- Auth ---

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Email ou mot de passe incorrect.");
  }
  const data = (await response.json()) as { access_token: string };
  return data.access_token;
}

export function fetchMe(): Promise<User> {
  return apiFetch<User>("/api/v1/auth/me");
}

// --- Candidats ---

export interface SearchParams {
  q?: string;
  secteur?: string;
  ville?: string;
  seniorite?: string;
  min_experience?: number;
  max_experience?: number;
  limit?: number;
  offset?: number;
}

export function searchCandidates(params: SearchParams): Promise<Page<Candidate>> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "" && value !== null) {
      query.set(key, String(value));
    }
  }
  return apiFetch<Page<Candidate>>(`/api/v1/candidates/search?${query.toString()}`);
}

export function getCandidate(id: string): Promise<CandidateDetail> {
  return apiFetch<CandidateDetail>(`/api/v1/candidates/${id}`);
}

export function getStats(): Promise<Stats> {
  return apiFetch<Stats>("/api/v1/candidates/stats");
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export function createCandidate(data: CandidateInput): Promise<Candidate> {
  return apiFetch<Candidate>("/api/v1/candidates", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function updateCandidate(id: string, data: CandidateInput): Promise<Candidate> {
  return apiFetch<Candidate>(`/api/v1/candidates/${id}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function deleteCandidate(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/candidates/${id}`, { method: "DELETE" });
}

// --- Documents ---

export async function uploadDocument(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<UploadResult>("/api/v1/documents/upload", { method: "POST", body: form });
}

export function processDocument(documentId: string): Promise<Candidate> {
  return apiFetch<Candidate>(`/api/v1/documents/${documentId}/process`, { method: "POST" });
}

export function getDownloadUrl(documentId: string): Promise<{ url: string; expires_in: number }> {
  return apiFetch(`/api/v1/documents/${documentId}/download-url`);
}
