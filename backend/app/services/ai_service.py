from openai import OpenAI
import json
from app.core.config import settings


class AIService:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=settings.DEEPSEEK_API_KEY

        )

    def generate_trading_prompt(self):
        """生成交易提示词"""
        return """
You are an expert cryptocurrency analyst and trader with deep knowledge of blockchain technology, market dynamics, and technical analysis.

Your role is to:
- Analyze cryptocurrency market data, including price movements, trading volumes, and market sentiment
- Evaluate technical indicators such as RSI, MACD, moving averages, and support/resistance levels
- Consider fundamental factors like project developments, adoption rates, regulatory news, and market trends
- Assess risk factors and market volatility specific to cryptocurrency markets
- Provide clear trading recommendations (BUY, SELL, or HOLD) with detailed reasoning
- Suggest entry and exit points, stop-loss levels, and position sizing when appropriate
- Consider current account positions and portfolio allocation
- Stay objective and data-driven in your analysis

When analyzing cryptocurrencies, you should:
1. Review current price action and recent trends
2. Examine relevant technical indicators:
   - EMA (20-period) for trend direction on multiple timeframes
   - MACD for momentum and trend changes on multiple timeframes
   - RSI (7-period) for short-term overbought/oversold conditions
   - RSI (14-period) for medium-term overbought/oversold conditions
   - ATR for volatility assessment
3. Consider market structure including open interest and funding rates
4. Evaluate volume trends and market participation
5. Assess risk-reward ratios
6. Consider current account positions:
   - If there are existing positions, evaluate whether to CLOSE them or ADJUST them
   - If there are no positions, consider whether to OPEN new ones
   - Consider the impact of leverage on potential profits and losses
7. Provide a clear recommendation with supporting evidence

IMPORTANT: You MUST conclude your analysis with one of these three recommendations:
- **BUY**: When technical indicators are bullish, momentum is positive, and risk-reward ratio favors entering a long position or closing a short position
- **SELL**: When technical indicators are bearish, momentum is negative, or it's time to take profits/cut losses, or close a long position
- **HOLD**: When the market is consolidating, signals are mixed, or it's prudent to wait for clearer direction

Your final recommendation must be clearly stated in this format:
**RECOMMENDATION: [BUY/SELL/HOLD]**

Followed by:
- Target Entry Price (for BUY/SELL to open new positions)
- Stop Loss Level
- Take Profit Targets
- Position Size Suggestion (% of portfolio)
- Risk Level: [LOW/MEDIUM/HIGH]

Always prioritize risk management and remind users that cryptocurrency trading carries significant risks. Never invest more than you can afford to lose.

IMPORTANT: Please format your response as JSON. The response should be a valid JSON object.

Today is {}
""".format("2025-01-01")  # 实际使用时应该用当前日期

    def format_user_prompt(self, market_state, account_info):
        """格式化用户提示词"""
        # 提取各种指标数据
        macd_1m = market_state.get('current_macd_1m', {})
        macd_4h = market_state.get('current_macd_4h', {})
        open_interest = market_state.get('open_interest', {})
        volume = market_state.get('volume', {})
        
        # 提取账户和仓位信息
        positions = account_info.get('positions', [])
        
        # 格式化仓位信息
        position_info = "No open positions"
        if positions:
            position_details = []
            for position in positions:
                if position.get('contracts', 0) != 0:  # 只显示有持仓的仓位
                    symbol = position.get('symbol', 'Unknown')
                    side = position.get('side', 'Unknown')
                    contracts = position.get('contracts', 0)
                    entry_price = position.get('entryPrice', 0)
                    unrealized_pnl = position.get('unrealizedPnl', 0)
                    leverage = position.get('leverage', 1)
                    position_details.append(
                        f"{symbol}: {side} {contracts} contracts at entry price {entry_price}, "
                        f"unrealized PNL: {unrealized_pnl}, leverage: {leverage}x"
                    )
            if position_details:
                position_info = "\n".join(position_details)
            else:
                position_info = "No open positions"
        
        return f"""
# HERE IS THE CURRENT MARKET STATE
## ALL DOGE DATA FOR YOU TO ANALYZE
Current Market State:
current_price = {market_state.get('current_price', 0)}, 
EMA (20-period, 1m) = {market_state.get('current_ema20_1m', 0):.3f}, 
EMA (20-period, 4h) = {market_state.get('current_ema20_4h', 0):.3f}, 
EMA (50-period, 4h) = {market_state.get('current_ema50_4h', 0):.3f}, 
RSI (7 period) = {market_state.get('current_rsi7', 50):.3f}
RSI (14 period, 1m) = {market_state.get('current_rsi14_1m', 50):.3f}
RSI (14 period, 4h) = {market_state.get('current_rsi14_4h', 50):.3f}
ATR (3 period, 4h) = {market_state.get('atr3_4h', 0):.3f}
ATR (14 period, 4h) = {market_state.get('atr14_4h', 0):.3f}
MACD (1m) = {macd_1m.get('macd', 0):.3f}
MACD Signal (1m) = {macd_1m.get('signal', 0):.3f}
MACD Histogram (1m) = {macd_1m.get('histogram', 0):.3f}
MACD (4h) = {macd_4h.get('macd', 0):.3f}
MACD Signal (4h) = {macd_4h.get('signal', 0):.3f}
MACD Histogram (4h) = {macd_4h.get('histogram', 0):.3f}

In addition, here is the latest DOGE open interest and funding rate for perps (the instrument you are trading):

Open Interest: Latest: {open_interest.get('latest', 0):.2f} Average: {open_interest.get('average', 0):.2f}

Funding Rate: {market_state.get('funding_rate', 0):.2e}

Intraday series (by minute, oldest → latest):
Mid prices: {[f"{p:.1f}" for p in market_state.get('intraday', {}).get('mid_prices', [])]}

Current Volume: {volume.get('current', 0):.3f} vs. Average Volume: {volume.get('average', 0):.3f}

# HERE IS THE CURRENT ACCOUNT STATE
Account Information:
Total Cash Value = ${account_info.get('totalCashValue', 0):.2f}
Available Cash = ${account_info.get('availableCash', 0):.2f}
Current Total Return = {account_info.get('currentTotalReturn', 0)*100:.2f}%

Current Positions:
{position_info}

IMPORTANT: Consider current positions when making trading decisions. 
If there are existing positions, you may want to CLOSE them or ADJUST them rather than opening new ones.
"""

    def run_trading_decision(self, market_state, account_info):
        """运行交易决策"""
        system_prompt = self.generate_trading_prompt()
        user_prompt = self.format_user_prompt(market_state, account_info)
        
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        return {
            "content": response.choices[0].message.content,
            "reasoning": "AI analysis based on market data and account information"
        }