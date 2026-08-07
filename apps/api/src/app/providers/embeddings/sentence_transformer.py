"""Embeddings sentence-transformers (vrai sémantique) — OPTIONNEL.

Non installé par défaut (tire torch, lourd). Pour l'activer :
  1) ajouter la dépendance : `sentence-transformers` ;
  2) EMBEDDINGS_BACKEND=sentence-transformers dans .env.
Modèle par défaut : intfloat/multilingual-e5-base (dim 768). Les modèles e5
attendent un préfixe « query: » / « passage: ».
"""

from anyio import to_thread


class SentenceTransformerEmbeddingProvider:
    def __init__(self, model_name: str, dimension: int) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - dépend de l'install
            raise ImportError(
                "sentence-transformers n'est pas installé. Ajoute la dépendance, "
                "ou garde EMBEDDINGS_BACKEND=deterministic."
            ) from exc
        self._model = SentenceTransformer(model_name)
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    async def embed_query(self, text: str) -> list[float]:
        result = await to_thread.run_sync(self._encode, [f"query: {text}"])
        return result[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await to_thread.run_sync(self._encode, [f"passage: {t}" for t in texts])
