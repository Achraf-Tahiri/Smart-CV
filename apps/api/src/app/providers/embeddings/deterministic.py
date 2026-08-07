"""Embeddings déterministes (hachage) — défaut hors-ligne, sans dépendance lourde.

⚠️ NON SÉMANTIQUE : deux textes de sens proche n'ont PAS de vecteurs proches.
C'est un bouchon rapide et reproductible pour le développement, les tests et la
recherche hybride (dont la partie plein-texte reste pleinement fonctionnelle).
Pour une vraie recherche sémantique, basculer sur sentence-transformers
(EMBEDDINGS_BACKEND=sentence-transformers).
"""

import hashlib
import math


class DeterministicEmbeddingProvider:
    def __init__(self, dimension: int = 768) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed_one(self, text: str) -> list[float]:
        data = (text or "").encode("utf-8")
        values: list[float] = []
        counter = 0
        # On génère assez d'octets (SHA-256 = 32 o) jusqu'à remplir la dimension.
        while len(values) < self._dimension:
            digest = hashlib.sha256(data + counter.to_bytes(4, "big")).digest()
            for i in range(0, len(digest), 4):
                if len(values) >= self._dimension:
                    break
                raw = int.from_bytes(digest[i : i + 4], "big") / 2**32  # [0, 1)
                values.append(raw * 2 - 1)  # [-1, 1)
            counter += 1
        # Normalisation L2 (utile pour la distance cosinus).
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]
