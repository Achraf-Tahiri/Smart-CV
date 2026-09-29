/** Isolated, read-only portfolio preview. No database, storage, or provider access. */
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("../", import.meta.url));
const candidates = JSON.parse(await readFile(new URL("../demo/candidates.json", import.meta.url), "utf8"));
const WEB_PORT = 3105;
const API_PORT = 8105;
const user = {
  id: "00000000-0000-4000-8000-000000000099",
  email: "demo@example.com", full_name: "Compte de démonstration",
  role: "lecteur", is_active: true, created_at: "2026-09-01T09:00:00Z",
};
const tokens = { access_token: "synthetic-preview-token", refresh_token: "synthetic-preview-refresh", token_type: "bearer" };
const countBy = (key) => candidates.reduce((counts, candidate) => {
  counts[candidate[key]] = (counts[candidate[key]] ?? 0) + 1;
  return counts;
}, {});

export const server = createServer(async (req, res) => {
  const origin = req.headers.origin;
  if (origin === `http://127.0.0.1:${WEB_PORT}` || origin === `http://localhost:${WEB_PORT}`) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  const send = (status, body) => { res.writeHead(status); res.end(JSON.stringify(body)); };
  if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
  const url = new URL(req.url, `http://127.0.0.1:${API_PORT}`);
  if (url.pathname === "/health") return send(200, { mode: "synthetic-preview", status: "ok" });
  if (req.method === "POST" && url.pathname === "/api/v1/auth/login") {
    let body = "";
    for await (const chunk of req) {
      body += chunk.toString();
      if (body.length > 4096) return send(413, { detail: "Request too large" });
    }
    const form = new URLSearchParams(body);
    return form.get("username") === user.email && form.get("password") === "demo-only"
      ? send(200, tokens) : send(401, { detail: "Utilisez le compte de démonstration." });
  }
  if (url.pathname === "/api/v1/auth/logout" && req.method === "POST") {
    res.writeHead(204); res.end(); return;
  }
  if (req.headers.authorization !== `Bearer ${tokens.access_token}`) return send(401, { detail: "Connexion requise." });
  if (req.method !== "GET") return send(403, { detail: "Cette démonstration est en lecture seule." });
  if (url.pathname === "/api/v1/auth/me") return send(200, user);
  if (url.pathname === "/api/v1/candidates/stats") return send(200, {
    total: candidates.length, by_status: countBy("status"), by_secteur: countBy("secteur"), by_seniorite: countBy("seniorite"),
  });
  if (url.pathname === "/api/v1/candidates/search") {
    const params = url.searchParams;
    const name = (params.get("name") ?? "").toLocaleLowerCase();
    const filtered = candidates.filter((candidate) =>
      `${candidate.prenom} ${candidate.nom}`.toLocaleLowerCase().includes(name) &&
      (!params.get("secteur") || candidate.secteur === params.get("secteur")) &&
      (!params.get("ville") || candidate.ville.toLocaleLowerCase().includes(params.get("ville").toLocaleLowerCase())) &&
      (!params.get("min_experience") || candidate.annees_experience >= Number(params.get("min_experience")))
    );
    const limit = Math.max(1, Math.min(100, Number(params.get("limit")) || 10));
    const offset = Math.max(0, Number(params.get("offset")) || 0);
    return send(200, { total: filtered.length, limit, offset, items: filtered.slice(offset, offset + limit) });
  }
  const match = url.pathname.match(/^\/api\/v1\/candidates\/([^/]+)$/);
  if (match) {
    const candidate = candidates.find((item) => item.id === match[1]);
    return candidate ? send(200, candidate) : send(404, { detail: "Profil introuvable." });
  }
  send(404, { detail: "Route indisponible dans la démonstration." });
});
server.on("error", (error) => { console.error(error.message); process.exit(1); });
server.listen(API_PORT, "127.0.0.1", () => {
  console.log(`Synthetic preview: http://127.0.0.1:${WEB_PORT}\nLogin: demo@example.com / demo-only`);
  const next = spawn(process.execPath, ["node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", String(WEB_PORT)], {
    cwd: webRoot, stdio: "inherit",
    env: { ...process.env, SMART_CV_PREVIEW: "1", NEXT_PUBLIC_PREVIEW_MODE: "true", NEXT_PUBLIC_API_URL: `http://127.0.0.1:${API_PORT}` },
  });
  let stopping = false;
  const stop = () => {
    if (stopping) return;
    stopping = true; next.kill("SIGTERM"); server.close();
  };
  process.on("SIGINT", stop); process.on("SIGTERM", stop);
  next.on("error", (error) => { console.error(error.message); stop(); process.exitCode = 1; });
  next.on("exit", (code) => { server.close(); process.exitCode = stopping ? 0 : (code ?? 1); });
});
