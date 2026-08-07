"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Racine : renvoie vers la liste des candidats (qui redirige vers /login si besoin).
export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/candidates");
  }, [router]);
  return null;
}
