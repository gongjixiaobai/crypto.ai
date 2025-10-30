import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.binance_service import BinanceService

async def test_binance_service():
    """测试修改后的Binance服务"""
    try:
        print("Testing Binance service...")
        service = BinanceService()
        
        # 测试市场状态获取
        print("1. Testing market state fetch...")
        result = await service.get_current_market_state("BTC/USDT")
        print(f"Market state result: {result}")
        
        if "error" in result:
            print(f"Error in market state fetch: {result['error']}")
            return False
            
        print("Market state fetch successful!")
        return True
        
    except Exception as e:
        print(f"Error testing Binance service: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_binance_service())
    if success:
        print("Binance service test passed!")
    else:
        print("Binance service test failed!")