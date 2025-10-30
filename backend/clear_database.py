#!/usr/bin/env python3
"""
数据库清理脚本
用于清空nof1.ai项目中的所有数据表
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings
from app.models.trading import Base, Metrics, Chat, Trading

def clear_database():
    """清空数据库中的所有数据"""
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
        print("开始清理数据库...")
        
        # 删除所有表中的数据（按正确的顺序以避免外键约束问题）
        db.query(Trading).delete()
        db.query(Chat).delete()
        db.query(Metrics).delete()
        
        # 提交更改
        db.commit()
        print("数据库清理完成！")
        
    except Exception as e:
        print(f"清理数据库时出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 确认操作
    confirm = input("您确定要清空数据库中的所有数据吗？此操作不可恢复！(输入 'yes' 确认): ")
    if confirm.lower() == 'yes':
        clear_database()
    else:
        print("操作已取消。")