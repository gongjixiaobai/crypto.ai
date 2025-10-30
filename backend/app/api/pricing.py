from fastapi import APIRouter, HTTPException
from app.services.binance_service import BinanceService
import asyncio
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 创建全局Binance服务实例以复用连接
binance_service = BinanceService()

@router.get("/simple")
async def get_simple_pricing():
    """获取简化的加密货币价格数据（仅当前价格，性能优化版本）"""
    try:
        symbols = ["BTC", "ETH", "SOL", "BNB", "DOGE"]
        pricing = {}
        
        # 控制并发数量，避免触发API限制
        semaphore = asyncio.Semaphore(5)  # 增加到5个并发请求
        
        async def fetch_with_semaphore(symbol):
            async with semaphore:
                return await binance_service.get_current_price(f"{symbol}/USDT")
        
        # 并行获取所有符号的价格数据
        tasks = [
            fetch_with_semaphore(symbol)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            symbol = symbols[i].lower()
            if isinstance(result, Exception):
                logger.error(f"Exception fetching {symbols[i]} pricing: {result}")
                pricing[symbol] = {"current_price": 0, "error": str(result)}
            elif isinstance(result, dict) and "error" in result:
                logger.error(f"Error fetching {symbols[i]} pricing: {result['error']}")
                pricing[symbol] = {"current_price": 0, "error": result["error"]}
            else:
                pricing[symbol] = result
        
        return {
            "success": True,
            "data": {
                "pricing": pricing
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_simple_pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_pricing():
    """获取加密货币价格数据（完整版本，包含技术指标）"""
    try:
        symbols = ["BTC", "ETH", "SOL", "BNB", "DOGE"]
        pricing = {}
        
        # 控制并发数量，避免触发API限制
        semaphore = asyncio.Semaphore(3)  # 最多同时3个并发请求
        
        async def fetch_with_semaphore(symbol):
            async with semaphore:
                return await binance_service.get_current_market_state(f"{symbol}/USDT")
        
        # 并行获取所有符号的价格数据
        tasks = [
            fetch_with_semaphore(symbol)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            symbol = symbols[i].lower()
            if isinstance(result, Exception):
                logger.error(f"Exception fetching {symbols[i]} pricing: {result}")
                pricing[symbol] = {"current_price": 0, "error": str(result)}
            elif isinstance(result, dict) and "error" in result:
                logger.error(f"Error fetching {symbols[i]} pricing: {result['error']}")
                pricing[symbol] = {"current_price": 0, "error": result["error"]}
            else:
                pricing[symbol] = result
        
        return {
            "success": True,
            "data": {
                "pricing": pricing
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))