from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Hotel Hotspot Manager"
    SECRET_KEY: str = "changeme_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database (PostgreSQL - app db)
    DATABASE_URL: str = "postgresql+asyncpg://hoteluser:hotelpass123@localhost:5432/hotelhotspot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    CORS_ORIGINS: str = "http://localhost,http://localhost:80,http://localhost:5173"

    # Admin
    ADMIN_EMAIL: str = "admin@hotel.com"
    ADMIN_PASSWORD: str = "admin123"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
