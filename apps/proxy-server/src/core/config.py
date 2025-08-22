from pydantic import Field
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
        env_file = "../.env"  # Look for .env in parent directory
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert allowed_origins string to list
        if isinstance(self.allowed_origins, str) and self.allowed_origins:
            self.allowed_origins_list = [origin.strip() for origin in self.allowed_origins.split(",")]
        else:
            self.allowed_origins_list = []
    
    @property
    def origins_list(self):
        """Get allowed origins as list"""
        return self.allowed_origins_list


settings = Settings()