from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import cron, metrics, pricing, trading
from app.core.config import settings
from app.core.database import Base, engine
import uvicorn
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.sql.schema import MetaData

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建数据库表
try:
    # 使用类型转换来解决Pyright类型检查问题
    metadata = Base.metadata  # type: ignore
    metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

app = FastAPI(title=settings.PROJECT_NAME)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(cron.router, prefix="/api/cron", tags=["cron"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(pricing.router, prefix="/api/pricing", tags=["pricing"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])

@app.get("/")
async def root():
    return {"message": "Welcome to nof1.ai clone backend"}

# 添加应用生命周期事件处理器
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")

if __name__ == "__main__":
    try:
        uvicorn.run("app.main:app", host="38.175.194.75", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise