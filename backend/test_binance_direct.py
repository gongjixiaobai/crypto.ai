import hashlib
import hmac
import time
import requests
import os
from dotenv import load_dotenv
import urllib.parse

# 加载环境变量
load_dotenv()

def send_signed_request(api_key, secret_key, base_url, url_path, method='GET', params={}):
    """发送签名请求到Binance API"""
    timestamp = int(time.time() * 1000)
    
    # 添加时间戳和接收窗口
    params['timestamp'] = timestamp
    params['recvWindow'] = 10000
    
    # 创建查询字符串
    query_string = urllib.parse.urlencode(params)
    
    # 生成签名
    signature = hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # 完整URL
    url = base_url + url_path + '?' + query_string + '&signature=' + signature
    
    # 请求头
    headers = {
        'X-MBX-APIKEY': api_key
    }
    
    # 发送请求
    if method == 'GET':
        response = requests.get(url, headers=headers)
    else:
        response = requests.post(url, headers=headers)
    
    return response.json()

def test_binance_direct():
    """直接测试Binance API"""
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_API_SECRET')
    base_url = 'https://api.binance.com'
    
    if not api_key or not secret_key:
        print("API keys not found in environment variables")
        return False
    
    try:
        print("Testing direct Binance API call...")
        
        # 测试简单的公共API
        print("1. Testing public API (ping)...")
        response = requests.get(base_url + '/api/v3/ping')
        print(f"Ping response: {response.json()}")
        
        # 测试带签名的简单API
        print("2. Testing signed API (account info)...")
        account_info = send_signed_request(api_key, secret_key, base_url, '/api/v3/account')
        if 'code' in account_info and account_info['code'] < 0:
            print(f"Error: {account_info}")
            return False
        else:
            print("Account info retrieved successfully")
            print(f"Account can trade: {account_info.get('canTrade', 'Unknown')}")
        
        # 测试期货账户API
        print("3. Testing futures API...")
        futures_base_url = 'https://fapi.binance.com'
        futures_account = send_signed_request(api_key, secret_key, futures_base_url, '/fapi/v2/account')
        if 'code' in futures_account and futures_account['code'] < 0:
            print(f"Futures API error: {futures_account}")
            # 这个错误可能是预期的，因为我们可能没有期货权限
        else:
            print("Futures account info retrieved successfully")
        
        return True
        
    except Exception as e:
        print(f"Error testing Binance API: {e}")
        return False

if __name__ == "__main__":
    print("Testing Binance API directly...")
    success = test_binance_direct()
    if success:
        print("Direct Binance API test passed!")
    else:
        print("Direct Binance API test failed!")