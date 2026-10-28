from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    postgres_user: str = "dkh"
    postgres_password: str = "change_me"
    postgres_db: str = "devknowledgehub"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    neo4j_user: str = "neo4j"
    neo4j_password: str = "change_me_too"
    neo4j_uri: str = "bolt://localhost:7687"

    # --- RAG / embeddings ---
    # "hash"                 : sans dépendance, déterministe (dev, tests, CI)
    # "sentence-transformers": vrai modèle sémantique (pip install -r requirements-ml.txt)
    embedding_backend: str = "hash"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384  # doit correspondre à la colonne vector(N) en base

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
