from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "crypto-ai"
    DATABASE_URL: str = "sqlite:///./crypto.db"
    BINANCE_API_KEY: str
    BINANCE_API_SECRET: str
    DEEPSEEK_API_KEY: str
    CRON_SECRET_KEY: str
    START_MONEY: float = 29
    # 更新CORS设置以允许来自前端开发服务器的请求
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:5173",  # 本地开发地址
        "http://38.175.194.75:9000"  # 生产环境前端地址
    ]
    
    # 可选的额外配置项
    NEXT_PUBLIC_URL: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()