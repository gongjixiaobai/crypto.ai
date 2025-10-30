import ccxt
import json
import logging
from app.core.config import settings
from typing import Dict, Any, Optional
from app.models.trading import Trading
from app.core.database import get_db

logger = logging.getLogger(__name__)


class TradingExecutor:
    def __init__(self):
        # 初始化Binance交易所连接，使用合约交易
        self.exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_API_SECRET,
            'options': {
                'defaultType': 'future',  # 使用合约交易
            },
            'enableRateLimit': True,
        })
        # Binance要求订单的名义价值至少为5 USDT
        self.MIN_NOTIONAL_VALUE = 5.0

    def execute_trade(self, symbol: str, decision: Dict[str, Any], chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        根据AI决策执行交易
        """
        try:
            recommendation = decision.get("recommendation", "").upper()
            
            if recommendation == "BUY":
                return self._execute_buy(symbol, decision, chat_id)
            elif recommendation == "SELL":
                return self._execute_sell(symbol, decision, chat_id)
            elif recommendation == "HOLD":
                # 即使是HOLD决策，也可以根据需要强制执行某些操作
                return self._execute_hold(symbol, decision, chat_id)
            else:
                return {
                    "status": "skipped",
                    "message": f"Unknown recommendation: {recommendation}"
                }
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _get_position_info(self, symbol: str) -> Dict[str, Any]:
        """获取当前持仓信息"""
        try:
            # 获取持仓信息
            positions = self.exchange.fetch_positions([symbol])
            # 过滤出当前交易对的持仓
            symbol_positions = [p for p in positions if p['symbol'] == symbol]
            if symbol_positions:
                return symbol_positions[0]
            return {}
        except Exception as e:
            logger.error(f"Error fetching position info: {str(e)}")
            return {}

    def _set_leverage(self, symbol: str, leverage: int = 5):
        """设置杠杆"""
        try:
            # 使用正确的API方法设置杠杆
            # 对于期货合约，使用futures API
            if hasattr(self.exchange, 'fapiPrivate_post_leverage'):
                self.exchange.fapiPrivate_post_leverage({
                    'symbol': symbol.replace('/', ''),
                    'leverage': leverage
                })
            elif hasattr(self.exchange, 'dapiPrivate_post_leverage'):
                self.exchange.dapiPrivate_post_leverage({
                    'symbol': symbol.replace('/', ''),
                    'leverage': leverage
                })
            else:
                # 尝试使用通用方法
                self.exchange.load_markets()
                market = self.exchange.market(symbol)
                if hasattr(self.exchange, 'set_leverage'):
                    self.exchange.set_leverage(leverage, symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
        except Exception as e:
            logger.warning(f"Failed to set leverage for {symbol}: {str(e)}")

    def _save_trade_to_db(self, symbol: str, operation: str, amount: float, price: float, 
                         leverage: Optional[int] = None, stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                         chat_id: Optional[str] = None):
        """保存交易记录到数据库"""
        db = None
        try:
            # 获取数据库会话
            db = next(get_db())
            
            # 创建交易记录
            trade = Trading(
                symbol=symbol,
                operation=operation,
                amount=amount,
                pricing=price,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                chat_id=chat_id
            )
            
            # 保存到数据库
            db.add(trade)
            db.commit()
            db.refresh(trade)
            
            logger.info(f"Trade saved to database: {trade.id}")
            return trade
        except Exception as e:
            logger.error(f"Error saving trade to database: {str(e)}")
            # 回滚事务
            if db:
                try:
                    db.rollback()
                except:
                    pass
            return None
        finally:
            # 关闭数据库会话
            if db:
                try:
                    db.close()
                except:
                    pass

    def _execute_buy(self, symbol: str, decision: Dict[str, Any], chat_id: Optional[str] = None) -> Dict[str, Any]:
        """执行买入交易"""
        try:
            # 获取当前持仓信息
            position_info = self._get_position_info(symbol)
            position_amount = position_info.get('contracts', 0) if position_info else 0
            side = position_info.get('side', '') if position_info else ''
            
            # 获取账户余额
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
            
            # 设置5倍杠杆
            self._set_leverage(symbol, 5)
            
            # 根据当前持仓情况决定操作
            if position_amount == 0:
                # 无持仓，开多仓
                if usdt_balance <= 0:
                    return {
                        "status": "failed",
                        "message": "Insufficient USDT balance"
                    }
                
                # 计算买入数量（使用部分资金以降低风险）
                entry_price = decision.get("target_entry_price") or decision.get("entry_price", 0)
                if not entry_price or entry_price <= 0:
                    # 如果没有指定入场价，使用当前市场价格
                    ticker = self.exchange.fetch_ticker(symbol)
                    entry_price = ticker['last']
                
                # 确保entry_price不是None且大于0
                if not entry_price or entry_price <= 0:
                    return {
                        "status": "failed",
                        "message": "Invalid entry price"
                    }
                
                # 使用建议的仓位大小或默认3%的可用资金进行交易
                position_size_str = decision.get("position_size_suggestion", "3%") or "3%"
                if isinstance(position_size_str, str) and position_size_str.endswith('%'):
                    try:
                        position_size_pct = float(position_size_str.replace("%", "")) / 100
                    except ValueError:
                        position_size_pct = 0.03  # 默认3%
                else:
                    position_size_pct = 0.03  # 默认3%
                    
                amount_to_spend = usdt_balance * position_size_pct
                
                # 确保订单金额满足最小要求
                if amount_to_spend < self.MIN_NOTIONAL_VALUE:
                    amount_to_spend = self.MIN_NOTIONAL_VALUE
                
                # 计算合约数量（考虑杠杆）
                amount = (amount_to_spend * 5) / entry_price
                
                # 创建买入订单
                order = self.exchange.create_market_buy_order(symbol, amount)
                
                # 保存交易记录到数据库
                self._save_trade_to_db(
                    symbol=symbol,
                    operation="BUY",
                    amount=amount,
                    price=entry_price,
                    leverage=5,
                    chat_id=chat_id
                )
                
                logger.info(f"Long position opened: {order}")
                return {
                    "status": "success",
                    "message": f"Long position opened successfully with 5x leverage",
                    "order": order,
                    "leverage": 5,
                    "action": "OPEN_LONG",
                    "position_size": position_size_str,
                    "amount_usdt": amount_to_spend
                }
            elif position_amount > 0 and side == 'short':
                # 当前持有空头仓位，需要平空
                # 平仓数量为当前持仓数量
                order = self.exchange.create_market_buy_order(symbol, abs(position_amount))
                
                # 保存交易记录到数据库
                self._save_trade_to_db(
                    symbol=symbol,
                    operation="BUY",
                    amount=abs(position_amount),
                    price=0,  # 平仓价格需要从订单中获取
                    leverage=None,
                    chat_id=chat_id
                )
                
                logger.info(f"Short position closed: {order}")
                return {
                    "status": "success",
                    "message": f"Short position closed successfully",
                    "order": order,
                    "action": "CLOSE_SHORT"
                }
            elif position_amount < 0 and side == 'short':
                # 当前持有空头仓位，需要平空
                # 平仓数量为当前持仓数量
                order = self.exchange.create_market_buy_order(symbol, abs(position_amount))
                
                # 保存交易记录到数据库
                self._save_trade_to_db(
                    symbol=symbol,
                    operation="BUY",
                    amount=abs(position_amount),
                    price=0,  # 平仓价格需要从订单中获取
                    leverage=None,
                    chat_id=chat_id
                )
                
                logger.info(f"Short position closed: {order}")
                return {
                    "status": "success",
                    "message": f"Short position closed successfully",
                    "order": order,
                    "action": "CLOSE_SHORT"
                }
            else:
                # 已经持有多头仓位或无明确操作
                return {
                    "status": "skipped",
                    "message": "Already in long position or no action needed",
                    "action": "HOLD_LONG"
                }
        except Exception as e:
            logger.error(f"Error executing buy order: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to execute BUY order: {str(e)}"
            }

    def _execute_sell(self, symbol: str, decision: Dict[str, Any], chat_id: Optional[str] = None) -> Dict[str, Any]:
        """执行卖出交易"""
        try:
            # 获取当前持仓信息
            position_info = self._get_position_info(symbol)
            position_amount = position_info.get('contracts', 0) if position_info else 0
            side = position_info.get('side', '') if position_info else ''
            
            # 获取账户余额
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
            
            # 设置5倍杠杆
            self._set_leverage(symbol, 5)
            
            # 根据当前持仓情况决定操作
            if position_amount == 0:
                # 无持仓，开空仓
                if usdt_balance <= 0:
                    return {
                        "status": "failed",
                        "message": "Insufficient USDT balance"
                    }
                
                # 计算卖出数量（使用部分资金以降低风险）
                entry_price = decision.get("target_entry_price") or decision.get("entry_price", 0)
                if not entry_price or entry_price <= 0:
                    # 如果没有指定入场价，使用当前市场价格
                    ticker = self.exchange.fetch_ticker(symbol)
                    entry_price = ticker['last']
                
                # 确保entry_price不是None且大于0
                if not entry_price or entry_price <= 0:
                    return {
                        "status": "failed",
                        "message": "Invalid entry price"
                    }
                
                # 使用建议的仓位大小或默认3%的可用资金进行交易
                position_size_str = decision.get("position_size_suggestion", "3%") or "3%"
                if isinstance(position_size_str, str) and position_size_str.endswith('%'):
                    try:
                        position_size_pct = float(position_size_str.replace("%", "")) / 100
                    except ValueError:
                        position_size_pct = 0.03  # 默认3%
                else:
                    position_size_pct = 0.03  # 默认3%
                    
                amount_to_spend = usdt_balance * position_size_pct
                
                # 确保订单金额满足最小要求
                if amount_to_spend < self.MIN_NOTIONAL_VALUE:
                    amount_to_spend = self.MIN_NOTIONAL_VALUE
                
                # 计算合约数量（考虑杠杆）
                amount = (amount_to_spend * 5) / entry_price
                
                # 创建卖出订单
                order = self.exchange.create_market_sell_order(symbol, amount)
                
                # 保存交易记录到数据库
                self._save_trade_to_db(
                    symbol=symbol,
                    operation="SELL",
                    amount=amount,
                    price=entry_price,
                    leverage=5,
                    chat_id=chat_id
                )
                
                logger.info(f"Short position opened: {order}")
                return {
                    "status": "success",
                    "message": f"Short position opened successfully with 5x leverage",
                    "order": order,
                    "leverage": 5,
                    "action": "OPEN_SHORT",
                    "position_size": position_size_str,
                    "amount_usdt": amount_to_spend
                }
            elif position_amount > 0 and side == 'long':
                # 当前持有多头仓位，需要平多
                # 平仓数量为当前持仓数量
                order = self.exchange.create_market_sell_order(symbol, position_amount)
                
                # 保存交易记录到数据库
                self._save_trade_to_db(
                    symbol=symbol,
                    operation="SELL",
                    amount=position_amount,
                    price=0,  # 平仓价格需要从订单中获取
                    leverage=None,
                    chat_id=chat_id
                )
                
                logger.info(f"Long position closed: {order}")
                return {
                    "status": "success",
                    "message": f"Long position closed successfully",
                    "order": order,
                    "action": "CLOSE_LONG"
                }
            elif position_amount < 0 and side == 'short':
                # 已经持有空头仓位，无需再开空
                return {
                    "status": "skipped",
                    "message": "Already in short position",
                    "action": "HOLD_SHORT"
                }
            else:
                # 其他情况
                return {
                    "status": "skipped",
                    "message": "No action needed",
                    "action": "NO_ACTION"
                }
        except Exception as e:
            logger.error(f"Error executing sell order: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to execute SELL order: {str(e)}"
            }

    def _execute_hold(self, symbol: str, decision: Dict[str, Any], chat_id: Optional[str] = None) -> Dict[str, Any]:
        """执行持有操作（可以用于其他操作，如调整止损等）"""
        # 在HOLD情况下，我们通常不执行任何交易
        # 但可以根据需要实现其他逻辑，如调整现有仓位的止损等
        
        return {
            "status": "skipped",
            "message": "HOLD recommendation - no trade executed",
            "details": "AI recommends holding current position"
        }