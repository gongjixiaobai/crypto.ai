import asyncio
import json
from app.services.binance_service import BinanceService
from app.services.ai_service import AIService

async def test_indicators():
    print("Testing market indicators...")
    
    # 创建服务实例
    binance_service = BinanceService()
    ai_service = AIService()
    
    # 获取市场状态
    market_state = await binance_service.get_current_market_state("BTC/USDT")
    
    # 模拟账户信息
    account_info = {
        "currentTotalReturn": 0.05,
        "availableCash": 10000,
        "totalCashValue": 10500
    }
    
    print("Market State:")
    print(f"  Current Price: {market_state.get('current_price', 0)}")
    print(f"  EMA 20 (1m): {market_state.get('current_ema20_1m', 0)}")
    print(f"  EMA 20 (4h): {market_state.get('current_ema20_4h', 0)}")
    print(f"  EMA 50 (4h): {market_state.get('current_ema50_4h', 0)}")
    print(f"  RSI 7: {market_state.get('current_rsi7', 0)}")
    print(f"  RSI 14 (1m): {market_state.get('current_rsi14_1m', 0)}")
    print(f"  RSI 14 (4h): {market_state.get('current_rsi14_4h', 0)}")
    
    macd_1m = market_state.get('current_macd_1m', {})
    print(f"  MACD (1m): {macd_1m.get('macd', 0)}")
    print(f"  MACD Signal (1m): {macd_1m.get('signal', 0)}")
    
    macd_4h = market_state.get('current_macd_4h', {})
    print(f"  MACD (4h): {macd_4h.get('macd', 0)}")
    print(f"  MACD Signal (4h): {macd_4h.get('signal', 0)}")
    
    print(f"  ATR (3 period, 4h): {market_state.get('atr3_4h', 0)}")
    print(f"  ATR (14 period, 4h): {market_state.get('atr14_4h', 0)}")
    
    open_interest = market_state.get('open_interest', {})
    print(f"  Open Interest - Latest: {open_interest.get('latest', 0)}")
    print(f"  Open Interest - Average: {open_interest.get('average', 0)}")
    
    print(f"  Funding Rate: {market_state.get('funding_rate', 0)}")
    
    volume = market_state.get('volume', {})
    print(f"  Current Volume: {volume.get('current', 0)}")
    print(f"  Average Volume: {volume.get('average', 0)}")
    
    # 测试AI服务格式化
    formatted_prompt = ai_service.format_user_prompt(market_state, account_info)
    print("\nFormatted Prompt for AI:")
    print(formatted_prompt)

if __name__ == "__main__":
    asyncio.run(test_indicators())