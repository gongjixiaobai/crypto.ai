import ccxt
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_binance_connection():
    """测试Binance连接"""
    try:
        # 创建Binance交易所实例
        exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_API_SECRET'),
            'options': {'defaultType': 'future'},
            'timeout': 30000,
        })
        
        # 启用详细日志记录
        exchange.verbose = True
        
        # 检查API密钥
        print("Checking API credentials...")
        if exchange.check_required_credentials(False):
            print("API credentials are valid")
        else:
            print("API credentials are invalid or missing")
            return False
            
        # 测试公共API调用（避免需要特殊权限的调用）
        print("Testing public API call...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"BTC/USDT price: {ticker['last']}")
        
        # 测试有限的私有API调用
        print("Testing private API call...")
        # 只获取特定交易对的信息，而不是所有资产信息
        orders = exchange.fetch_orders('BTC/USDT', limit=1)
        print(f"Fetched {len(orders)} recent orders for BTC/USDT")
        
        return True
        
    except ccxt.AuthenticationError as e:
        print(f"Authentication error: {e}")
        return False
    except ccxt.ExchangeError as e:
        print(f"Exchange error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Binance connection...")
    success = test_binance_connection()
    if success:
        print("Binance connection test passed!")
    else:
        print("Binance connection test failed!")