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

export function getCandidate(id: string): Promise<Candidate> {
  return apiFetch<Candidate>(`/api/v1/candidates/${id}`);
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
