#!/usr/bin/env python3
"""
数据库检查脚本
用于检查nof1.ai项目中的数据表记录数
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings
from app.models.trading import Metrics, Chat, Trading

def check_database():
    """检查数据库中的数据"""
    print("正在连接到数据库...")
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        pool_recycle=300
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("检查数据库中的记录数...")
        
        # 查询各表的记录数
        metrics_count = db.query(Metrics).count()
        chats_count = db.query(Chat).count()
        tradings_count = db.query(Trading).count()
        
        print(f"Metrics 表记录数: {metrics_count}")
        print(f"Chats 表记录数: {chats_count}")
        print(f"Tradings 表记录数: {tradings_count}")
        print("检查完成！")
        
    except Exception as e:
        print(f"检查数据库时出错: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database()