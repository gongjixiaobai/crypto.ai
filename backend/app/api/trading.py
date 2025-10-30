from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm.session import Session
from app.core.database import get_db
from app.models.trading import Chat, Trading
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/chats")
async def get_chats(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取聊天记录"""
    try:
        # 查询聊天记录，按创建时间倒序排列
        chats = db.query(Chat).order_by(Chat.created_at.desc()).offset(skip).limit(limit).all()
        
        # 格式化返回数据
        chat_list = []
        for chat in chats:
            try:
                # 尝试解析chat内容为JSON
                chat_content = json.loads(chat.chat) if chat.chat else {}
            except json.JSONDecodeError:
                # 如果不是有效的JSON，直接使用原始内容
                chat_content = {"content": chat.chat}
            
            chat_list.append({
                "id": chat.id,
                "model": chat.model,
                "chat": chat_content,
                "reasoning": chat.reasoning,
                "user_prompt": chat.user_prompt,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None
            })
        
        return {
            "success": True,
            "data": chat_list,
            "total": len(chat_list),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/completed-trades")
async def get_completed_trades(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取已完成的交易记录"""
    try:
        # 查询交易记录，按创建时间倒序排列，关联聊天记录
        trades = db.query(Trading).join(Chat).order_by(Trading.created_at.desc()).offset(skip).limit(limit).all()
        
        # 格式化返回数据
        trade_list = []
        for trade in trades:
            trade_list.append({
                "id": trade.id,
                "symbol": trade.symbol,
                "operation": trade.operation,
                "leverage": trade.leverage,
                "amount": trade.amount,
                "pricing": trade.pricing,
                "stop_loss": trade.stop_loss,
                "take_profit": trade.take_profit,
                "created_at": trade.created_at.isoformat() if trade.created_at else None,
                "chat_id": trade.chat_id,
                "chat_model": trade.chat.model if trade.chat else None,
                "chat_created_at": trade.chat.created_at.isoformat() if trade.chat and trade.chat.created_at else None
            })
        
        return {
            "success": True,
            "data": trade_list,
            "total": len(trade_list),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))