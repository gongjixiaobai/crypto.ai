import asyncio
import json
from app.services.trading_executor import TradingExecutor

async def test_trade_execution():
    print("Testing trade execution...")
    
    # 创建交易执行器
    executor = TradingExecutor()
    
    # 模拟一个BUY决策
    buy_decision = {
        "recommendation": "BUY",
        "entry_price": 0.200,
        "stop_loss": 0.190,
        "take_profit_targets": [0.210, 0.220],
        "position_size_suggestion": "50%",
        "risk_level": "LOW"
    }
    
    print("Executing BUY decision...")
    result = executor.execute_trade("DOGE/USDT", buy_decision)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # 模拟一个SELL决策
    sell_decision = {
        "recommendation": "SELL",
        "entry_price": 0.200,
        "stop_loss": 0.210,
        "take_profit_targets": [0.190, 0.180],
        "position_size_suggestion": "50%",
        "risk_level": "LOW"
    }
    
    print("\nExecuting SELL decision...")
    result = executor.execute_trade("DOGE/USDT", sell_decision)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # 模拟一个HOLD决策
    hold_decision = {
        "recommendation": "HOLD",
        "reasoning": "Market is consolidating, wait for breakout",
        "risk_level": "LOW"
    }
    
    print("\nExecuting HOLD decision...")
    result = executor.execute_trade("DOGE/USDT", hold_decision)
    print(f"Result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_trade_execution())