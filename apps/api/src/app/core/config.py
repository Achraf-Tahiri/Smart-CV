"""Configuration de l'application, chargée depuis l'environnement (.env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application.

    Les valeurs proviennent des variables d'environnement (ou d'un fichier .env).
    Toutes ont une valeur par défaut, pour que l'API démarre sans configuration
    en développement. Les variables inconnues du .env sont ignorées.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "New Smart CV"
    app_env: str = "local"  # local | staging | production
    log_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR
    api_port: int = 8000
    version: str = "0.1.0"

    # --- Base de données (PostgreSQL + asyncpg) ---
    database_url: str = "postgresql+asyncpg://nscv:change-me@localhost:5432/nscv"

    # --- Authentification JWT (Phase 1.2) ---
    # ⚠️ En production, JWT_SECRET_KEY DOIT être une longue chaîne aléatoire secrète.
    jwt_secret_key: str = "change-me-utiliser-une-longue-chaine-aleatoire"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # --- Stockage fichiers (S3 / MinIO — Phase 1.4) ---
    s3_endpoint_url: str = "http://minio:9000"  # endpoint interne (réseau docker)
    # Endpoint PUBLIC pour signer les URLs de téléchargement (joignable par le navigateur).
    # En dev : http://localhost:9000. Vide => on retombe sur s3_endpoint_url.
    s3_public_endpoint_url: str = ""
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "cv-documents"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    max_upload_mb: int = 20  # taille maximale d'un document uploadé

    # --- Fournisseurs LLM (Phase 2.2) ---
    llm_provider_order: str = "groq,gemini,hf"  # ordre de la cascade
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    hf_api_token: str = ""
    hf_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    llm_timeout_seconds: float = 60.0
    # Longueur max du texte de CV envoyé au LLM (le POC tronquait à 4000 : trop court).
    llm_max_input_chars: int = 20000

    # --- Extraction de texte / OCR (Phase 2.3) ---
    tesseract_lang: str = "fra+eng"
    ocr_dpi: int = 300
    # Sous ce nombre de caractères extraits d'un PDF, on bascule en OCR (PDF scanné).
    ocr_min_chars: int = 50

    # --- Embeddings (Phase 2.3) ---
    # "deterministic" (défaut, sans torch, non sémantique) | "sentence-transformers".
    embeddings_backend: str = "deterministic"
    embeddings_model: str = "intfloat/multilingual-e5-base"
    embeddings_dim: int = 768

    @property
    def llm_order(self) -> list[str]:
        """Liste ordonnée des fournisseurs LLM (robuste aux espaces/vides)."""
        return [p.strip().lower() for p in self.llm_provider_order.split(",") if p.strip()]

    @property
    def s3_signing_endpoint(self) -> str:
        """Endpoint utilisé pour signer les URLs (public si défini, sinon interne)."""
        return self.s3_public_endpoint_url or self.s3_endpoint_url

    @property
    def is_local(self) -> bool:
        """Vrai en environnement de développement local."""
        return self.app_env.lower() == "local"


# Instance unique, importée partout : `from app.core.config import settings`
settings = Settings()
