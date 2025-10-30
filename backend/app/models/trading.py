from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.functions import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import Integer, String, DateTime, Text, JSON
import uuid
from app.core.database import Base


class Metrics(Base):
    __tablename__ = "metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    model = Column(String, nullable=False)
    metrics = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model = Column(String, default="Deepseek")
    chat = Column(Text, default="<no chat>")
    reasoning = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tradings = relationship("Trading", back_populates="chat")


class Trading(Base):
    __tablename__ = "tradings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    leverage = Column(Integer, nullable=True)
    amount = Column(Integer, nullable=True)
    pricing = Column(Integer, nullable=True)
    stop_loss = Column(Integer, nullable=True)
    take_profit = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"))
    chat = relationship("Chat", back_populates="tradings")