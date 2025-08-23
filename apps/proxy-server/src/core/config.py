from pydantic import Field, computed_field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    app_name: str = "chat-proxy"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    reload: bool = False
    
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    n8n_webhook_url: str = Field(..., env="N8N_WEBHOOK_URL")
    n8n_api_key: str = Field(..., env="N8N_API_KEY")
    
    allowed_origins: str = Field(default="", env="ALLOWED_ORIGINS")
    cors_allow_credentials: bool = True
    
    session_secret_key: str = Field(..., env="SESSION_SECRET_KEY")
    session_cookie_name: str = "chat_session_id"
    session_cookie_max_age: int = 86400  # 24 hours
    
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    class Config:
        env_file = ".env"  # Look for .env in current directory
        case_sensitive = False
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as list"""
        if isinstance(self.allowed_origins, str) and self.allowed_origins:
            return [origin.strip() for origin in self.allowed_origins.split(",")]
        return []
    
    @property
    def origins_list(self) -> List[str]:
        """Alias for allowed_origins_list"""
        return self.allowed_origins_list


settings = Settings()