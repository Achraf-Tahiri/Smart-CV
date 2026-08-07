"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/app/providers";

export function Nav() {
  const { user, logout } = useAuth();
  const router = useRouter();

  if (!user) return null;

  const canWrite = user.role === "admin" || user.role === "recruteur";

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="border-b bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="font-bold">
            New Smart CV
          </Link>
          <Link href="/dashboard" className="text-sm text-gray-600 hover:text-gray-900">
            Tableau de bord
          </Link>
          <Link href="/candidates" className="text-sm text-gray-600 hover:text-gray-900">
            Candidats
          </Link>
          {canWrite && (
            <Link href="/candidates/new" className="text-sm text-gray-600 hover:text-gray-900">
              Nouveau
            </Link>
          )}
          {canWrite && (
            <Link href="/upload" className="text-sm text-gray-600 hover:text-gray-900">
              Importer
            </Link>
          )}
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">
            {user.email} · {user.role}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded border px-2 py-1 hover:bg-gray-50"
          >
            Déconnexion
          </button>
        </div>
      </nav>
    </header>
  );
}
