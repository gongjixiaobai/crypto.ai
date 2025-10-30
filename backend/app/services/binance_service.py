import ccxt
import asyncio
import time
from app.core.config import settings
import logging
from typing import Dict, Any, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加简单的内存缓存
class SimpleCache:
    def __init__(self, ttl: int = 60):
        self.cache: Dict[str, tuple] = {}  # {key: (value, expiry_time)}
        self.ttl = ttl
        self.access_times: Dict[str, float] = {}  # 记录访问时间用于LRU
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                self.access_times[key] = time.time()
                return value
            else:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        expiry = time.time() + self.ttl
        self.cache[key] = (value, expiry)
        self.access_times[key] = time.time()
        
        # 如果缓存项过多，清理最久未访问的项
        if len(self.cache) > 100:  # 限制缓存大小
            self._cleanup()
    
    def _cleanup(self) -> None:
        # 清理过期项
        current_time = time.time()
        expired_keys = [key for key, (_, expiry) in self.cache.items() if current_time >= expiry]
        for key in expired_keys:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
        
        # 如果仍然过多，按访问时间清理
        if len(self.cache) > 100:
            sorted_keys = sorted(self.access_times.items(), key=lambda x: x[1])
            keys_to_remove = [key for key, _ in sorted_keys[:20]]  # 移除20个最久未访问的
            for key in keys_to_remove:
                del self.cache[key]
                del self.access_times[key]

# 创建缓存实例
pricing_cache = SimpleCache(ttl=30)  # 30秒缓存


class BinanceService:
    def __init__(self):
        # 修改配置以避免自动加载某些需要特殊权限的API端点
        self.exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_API_SECRET,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
                # 禁用自动加载某些API端点
                'fetchCurrencies': False,
            },
            'timeout': 30000,
            # 禁用某些可能导致问题的自动调用
            'enableRateLimit': True,
        })
        # 禁用详细日志记录以提高性能
        self.exchange.verbose = False

    async def get_current_price(self, symbol: str):
        """获取当前价格（优化版本，只获取必要数据）"""
        # 检查缓存
        cache_key = f"current_price_{symbol}"
        cached_result = pricing_cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached price for {symbol}")
            return cached_result
            
        try:
            logger.info(f"Fetching current price for {symbol}")
            normalized_symbol = symbol if '/' in symbol else f"{symbol}/USDT"
            
            # 直接获取ticker数据，只获取当前价格
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ticker, normalized_symbol
            )
            
            current_price = ticker.get('last') or ticker.get('close') or 0
            
            result = {
                'current_price': current_price
            }
            
            # 缓存结果
            pricing_cache.set(cache_key, result)
            
            return result
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error fetching price: {e}")
            return {"error": f"Authentication failed: {str(e)}"}
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching price: {e}")
            return {"error": f"Network error: {str(e)}"}
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching price: {e}")
            return {"error": f"Exchange error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            return {"error": str(e)}

    def calculate_ema(self, prices, period):
        """计算EMA指标"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        # 简单移动平均作为初始EMA
        sma = sum(prices[:period]) / period
        ema = sma
        multiplier = 2 / (period + 1)
        
        # 计算后续EMA值
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
            
        return ema

    def calculate_macd(self, prices, fast_period=12, slow_period=26, signal_period=9):
        """计算MACD指标"""
        if len(prices) < slow_period:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
        # 计算快速EMA和慢速EMA
        fast_ema = []
        slow_ema = []
        multiplier_fast = 2 / (fast_period + 1)
        multiplier_slow = 2 / (slow_period + 1)
        
        # 初始化EMA
        fast_sma = sum(prices[:fast_period]) / fast_period
        slow_sma = sum(prices[:slow_period]) / slow_period
        fast_ema_value = fast_sma
        slow_ema_value = slow_sma
        
        # 计算EMA序列
        for i, price in enumerate(prices):
            if i < fast_period - 1:
                fast_ema.append(fast_sma)
            else:
                fast_ema_value = (price - fast_ema_value) * multiplier_fast + fast_ema_value
                fast_ema.append(fast_ema_value)
                
            if i < slow_period - 1:
                slow_ema.append(slow_sma)
            else:
                slow_ema_value = (price - slow_ema_value) * multiplier_slow + slow_ema_value
                slow_ema.append(slow_ema_value)
        
        # 计算MACD线
        macd_line = [fast_ema[i] - slow_ema[i] for i in range(len(fast_ema))]
        
        # 计算信号线
        signal_line = []
        signal_sma = sum(macd_line[-signal_period:]) / signal_period if len(macd_line) >= signal_period else 0
        signal_ema = signal_sma
        
        for i, macd in enumerate(macd_line[-signal_period:]):
            if i == 0:
                signal_line.append(signal_sma)
            else:
                signal_ema = (macd - signal_ema) * (2 / (signal_period + 1)) + signal_ema
                signal_line.append(signal_ema)
        
        # 计算柱状图
        histogram = macd_line[-1] - (signal_line[-1] if signal_line else 0)
        
        return {
            "macd": macd_line[-1],
            "signal": signal_line[-1] if signal_line else 0,
            "histogram": histogram
        }

    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50  # 默认值
        
        # 计算价格变化
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # 分离正负变化
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # 计算平均增益和平均损失
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # 计算后续的平均值
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # 计算RSI
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    async def get_current_market_state(self, symbol: str):
        """获取当前市场状态"""
        # 检查缓存
        cache_key = f"market_state_{symbol}"
        cached_result = pricing_cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached market state for {symbol}")
            return cached_result
            
        try:
            logger.info(f"Fetching market state for {symbol}")
            normalized_symbol = symbol if '/' in symbol else f"{symbol}/USDT"
            
            # 检查交易所连接
            if not self.exchange.check_required_credentials(False):
                logger.error("Binance API credentials are missing or invalid")
                return {"error": "API credentials are missing or invalid"}
            
            # 使用公共API获取市场数据
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ticker, normalized_symbol
            )
            
            # 获取OHLCV数据（1分钟和4小时）
            ohlcv1m = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ohlcv, normalized_symbol, '1m', None, 100
            )
            
            ohlcv4h = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ohlcv, normalized_symbol, '4h', None, 50
            )
            
            closes1m = [float(candle[4]) for candle in ohlcv1m]
            closes4h = [float(candle[4]) for candle in ohlcv4h]
            
            # 计算技术指标
            current_price = ticker['last'] if ticker and 'last' in ticker else (closes1m[-1] if closes1m else 0)
            ema20_1m = self.calculate_ema(closes1m, 20)
            ema20_4h = self.calculate_ema(closes4h, 20) if len(closes4h) >= 20 else current_price
            ema50_4h = self.calculate_ema(closes4h, 50) if len(closes4h) >= 50 else current_price
            macd_data_1m = self.calculate_macd(closes1m)
            macd_data_4h = self.calculate_macd(closes4h, 12, 26, 9) if len(closes4h) >= 26 else {"macd": 0, "signal": 0, "histogram": 0}
            rsi7 = self.calculate_rsi(closes1m, 7)
            rsi14_1m = self.calculate_rsi(closes1m, 14)
            rsi14_4h = self.calculate_rsi(closes4h, 14) if len(closes4h) >= 14 else 50
            
            # 计算ATR指标
            atr3_4h = self.calculate_atr(ohlcv4h, 3) if len(ohlcv4h) >= 3 else 0
            atr14_4h = self.calculate_atr(ohlcv4h, 14) if len(ohlcv4h) >= 14 else 0
            
            # 获取持仓量和资金费率（如果支持）
            open_interest = 0
            funding_rate = 0
            try:
                # 尝试获取持仓量数据
                if hasattr(self.exchange, 'fapiPublicGetOpenInterest'):
                    open_interest_data = await asyncio.get_event_loop().run_in_executor(
                        None, self.exchange.fapiPublicGetOpenInterest, {'symbol': normalized_symbol.replace('/', '')}
                    )
                    open_interest = float(open_interest_data['openInterest']) if open_interest_data else 0
                
                # 尝试获取资金费率
                if hasattr(self.exchange, 'fapiPublicGetPremiumIndex'):
                    premium_index = await asyncio.get_event_loop().run_in_executor(
                        None, self.exchange.fapiPublicGetPremiumIndex, {'symbol': normalized_symbol.replace('/', '')}
                    )
                    funding_rate = float(premium_index[0]['lastFundingRate']) if premium_index and len(premium_index) > 0 else 0
            except Exception as e:
                logger.warning(f"Could not fetch open interest or funding rate: {e}")
            
            # 计算平均持仓量（最近10个数据点）
            avg_open_interest = open_interest  # 简化处理
            
            # 获取交易量数据
            current_volume = ticker.get('baseVolume', 0) if ticker else 0
            avg_volume = sum([float(candle[5]) for candle in ohlcv4h[-10:]]) / 10 if len(ohlcv4h) >= 10 else current_volume
            
            result = {
                'current_price': current_price,
                'current_ema20_1m': ema20_1m,
                'current_ema20_4h': ema20_4h,
                'current_ema50_4h': ema50_4h,
                'current_macd_1m': macd_data_1m,
                'current_macd_4h': macd_data_4h,
                'current_rsi7': rsi7,
                'current_rsi14_1m': rsi14_1m,
                'current_rsi14_4h': rsi14_4h,
                'atr3_4h': atr3_4h,
                'atr14_4h': atr14_4h,
                'open_interest': {
                    'latest': open_interest,
                    'average': avg_open_interest
                },
                'funding_rate': funding_rate,
                'volume': {
                    'current': current_volume,
                    'average': avg_volume
                },
                'intraday': {
                    'mid_prices': closes1m[-10:] if len(closes1m) >= 10 else closes1m,
                    'ema20_series': [self.calculate_ema(closes1m[:i], 20) for i in range(20, len(closes1m)+1)][-10:] if len(closes1m) >= 20 else [],
                    'macd_series': [self.calculate_macd(closes1m[:i])['macd'] for i in range(26, len(closes1m)+1)][-10:] if len(closes1m) >= 26 else [],
                    'rsi7_series': [self.calculate_rsi(closes1m[:i], 7) for i in range(7, len(closes1m)+1)][-10:] if len(closes1m) >= 7 else [],
                    'rsi14_series': [self.calculate_rsi(closes1m[:i], 14) for i in range(14, len(closes1m)+1)][-10:] if len(closes1m) >= 14 else []
                },
                'long_term_context': {
                    'ema20_4h_series': [self.calculate_ema(closes4h[:i], 20) for i in range(20, len(closes4h)+1)][-10:] if len(closes4h) >= 20 else [],
                    'macd_4h_series': [self.calculate_macd(closes4h[:i], 12, 26, 9)['macd'] for i in range(26, len(closes4h)+1)][-10:] if len(closes4h) >= 26 else [],
                    'rsi14_4h_series': [self.calculate_rsi(closes4h[:i], 14) for i in range(14, len(closes4h)+1)][-10:] if len(closes4h) >= 14 else []
                }
            }
            
            # 缓存结果
            pricing_cache.set(cache_key, result)
            
            return result
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error fetching market state: {e}")
            return {"error": f"Authentication failed: {str(e)}"}
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching market state: {e}")
            return {"error": f"Network error: {str(e)}"}
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching market state: {e}")
            return {"error": f"Exchange error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching market state: {e}")
            return {"error": str(e)}

    def calculate_atr(self, ohlcv, period):
        """计算ATR指标"""
        if len(ohlcv) < period + 1:
            return 0
        
        tr_values = []
        for i in range(1, len(ohlcv)):
            high = float(ohlcv[i][2])
            low = float(ohlcv[i][3])
            prev_close = float(ohlcv[i-1][4])
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
        
        # 计算ATR
        atr = sum(tr_values[-period:]) / period
        return atr

    async def get_account_information_and_performance(self, initial_capital: float):
        """获取账户信息和性能"""
        try:
            logger.info("Fetching account information")
            
            # 检查交易所连接
            if not self.exchange.check_required_credentials(False):
                logger.error("Binance API credentials are missing or invalid")
                return {"error": "API credentials are missing or invalid"}
            
            # 使用简化的方法获取账户信息
            balance = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_balance
            )
            
            total_cash_value = balance['USDT']['total'] if 'USDT' in balance else 0
            available_cash = balance['USDT']['free'] if 'USDT' in balance else 0
            current_total_return = (total_cash_value - initial_capital) / initial_capital if initial_capital > 0 else 0
            
            # 获取持仓信息（如果支持）
            positions = []
            try:
                positions = await asyncio.get_event_loop().run_in_executor(
                    None, self.exchange.fetch_positions
                )
            except Exception as pos_error:
                logger.warning(f"Could not fetch positions: {pos_error}")
            
            return {
                'totalCashValue': total_cash_value,
                'availableCash': available_cash,
                'currentTotalReturn': current_total_return,
                'positions': positions
            }
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error fetching account info: {e}")
            return {"error": f"Authentication failed: {str(e)}"}
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching account info: {e}")
            return {"error": f"Network error: {str(e)}"}
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching account info: {e}")
            return {"error": f"Exchange error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching account info: {e}")
            return {"error": str(e)}