from jose import jwt
from app.core.config import settings
from datetime import datetime, timedelta


def verify_token(token: str) -> bool:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, settings.CRON_SECRET_KEY, algorithms=["HS256"])
        return True
    except:
        return False


def create_token() -> str:
    """创建JWT令牌"""
    payload = {
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.CRON_SECRET_KEY, algorithm="HS256")

    