from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "mysql+aiomysql://remediant:medagent123@localhost:3306/remediant"
    redis_url: str = "redis://localhost:6379/0"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "remediant"

    # Model adapters
    dashscope_api_key: str = ""

    # Model routing: "dashscope" only (Ollama removed)
    inference_backend: str = "dashscope"
    embedding_backend: str = "dashscope"
    reranker_backend: str = "dashscope"

    # MCP
    mcp_enabled: bool = True
    mcp_default_timeout: float = 10.0

    # Doubao (火山引擎) multimodal
    doubao_api_key: str = ""
    doubao_app_id: str = ""
    doubao_vision_model: str = "doubao-seed-2-0-lite-260215"
    doubao_vision_endpoint: str = ""  # 推理接入点 ID，如 ep-xxx

    # MinIO
    minio_bucket_reports: str = "remediant-reports"
    max_upload_size_mb: int = 20

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # App
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:80", "http://localhost"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
