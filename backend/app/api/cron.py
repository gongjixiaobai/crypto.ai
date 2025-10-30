from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.functions import func
from app.core.database import get_db
from app.services.binance_service import BinanceService
from app.services.ai_service import AIService
from app.services.trading_executor import TradingExecutor
from app.models.trading import Metrics as MetricsModel
from app.models.trading import Chat, Trading
from app.core.security import verify_token
from app.core.config import settings
import json
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# 最大指标数量
MAX_METRICS_COUNT = 100


def uniform_sample_with_boundaries(data: list, max_size: int) -> list:
    """均匀采样数组，保持首尾元素不变"""
    if len(data) <= max_size:
        return data

    result = []
    step = (len(data) - 1) / (max_size - 1)

    for i in range(max_size):
        index = round(i * step)
        result.append(data[index])

    return result


@router.get("/3-minutes-run-interval")
async def run_trading_decision(
    token: str = Query(..., description="Cron authentication token"),
    db: Session = Depends(get_db)
):
    """每3分钟执行一次AI交易决策"""
    # 验证token
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # 初始化服务
        binance_service = BinanceService()
        ai_service = AIService()
        trading_executor = TradingExecutor()
        
        # 获取市场状态和账户信息
        market_state = await binance_service.get_current_market_state("DOGE/USDT")
        account_info = await binance_service.get_account_information_and_performance(
            settings.START_MONEY
        )
        
        # 调用AI生成决策
        ai_response = ai_service.run_trading_decision(market_state, account_info)
        
        # 解析AI决策
        decision_content = ai_response["content"]
        decision_data = {}
        try:
            decision_data = json.loads(decision_content)
        except json.JSONDecodeError:
            logger.error("Failed to parse AI decision as JSON")
            decision_data = {"recommendation": "HOLD", "reasoning": "Failed to parse AI response"}
        
        # 保存决策到数据库
        chat = Chat(
            model="Deepseek",  # type: ignore
            chat=decision_content,  # type: ignore
            reasoning=ai_response["reasoning"],  # type: ignore
            user_prompt=json.dumps({  # type: ignore
                "market_state": market_state,
                "account_info": account_info
            })
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        # 执行交易，传递chat_id
        execution_result = trading_executor.execute_trade("DOGE/USDT", decision_data, chat.id)
        
        return {
            "message": "Trading decision executed successfully",
            "decision": decision_data,
            "execution_result": execution_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/20-seconds-metrics-interval")
async def collect_metrics(
    token: str = Query(..., description="Cron authentication token"),
    db: Session = Depends(get_db)
):
    """每20秒收集账户指标"""
    # 验证token
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # 初始化服务
        binance_service = BinanceService()
        
        # 获取账户信息
        account_info = await binance_service.get_account_information_and_performance(
            settings.START_MONEY
        )
        
        # 获取现有指标
        existing_metrics = db.query(MetricsModel).filter(
            MetricsModel.model == "Deepseek"  # type: ignore
        ).first()
        
        if not existing_metrics:
            # 创建新的指标记录
            existing_metrics = MetricsModel(
                name="20-seconds-metrics",  # type: ignore
                model="Deepseek",  # type: ignore
                metrics=[]  # type: ignore
            )
            db.add(existing_metrics)
            db.flush()
        
        # 添加新指标
        new_metric = {
            "accountInformationAndPerformance": account_info,
            "createdAt": datetime.now().isoformat()
        }
        
        # 将SQLAlchemy列转换为普通Python对象
        current_metrics = existing_metrics.metrics if existing_metrics.metrics is not None else []
        if not isinstance(current_metrics, list):
            current_metrics = []
        
        # 更新指标数据
        updated_metrics = current_metrics[-(MAX_METRICS_COUNT-1):] + [new_metric] if current_metrics else [new_metric]
        
        # 使用setattr来避免类型检查问题
        setattr(existing_metrics, 'metrics', updated_metrics)
        db.commit()
        
        return {
            "message": "Metrics collected successfully",
            "metrics_count": len(updated_metrics)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))