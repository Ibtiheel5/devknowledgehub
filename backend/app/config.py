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

    embedding_backend: str = "hash"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_timeout: int = 300

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
