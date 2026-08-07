"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Racine : renvoie vers le tableau de bord (qui redirige vers /login si besoin).
export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);
  return null;
}
