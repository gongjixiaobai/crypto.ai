#!/usr/bin/env python3
# 用于清空crypto.ai项目中的所有数据表

import sys
import os

# 将项目根目录添加到Python路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.trading import Chat, Metric, Pricing, CompletedTrade

def clear_all_tables():
    db = SessionLocal()
    try:
        # 清空所有表的数据
        db.query(Chat).delete()
        db.query(Metric).delete()
        db.query(Pricing).delete()
        db.query(CompletedTrade).delete()
        
        # 提交更改
        db.commit()
        print("所有数据表已清空")
    except Exception as e:
        print(f"清空数据表时出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 确认操作
    confirm = input("确定要清空所有数据表吗？(输入 'yes' 确认): ")
    if confirm.lower() == 'yes':
        clear_all_tables()
    else:
        print("操作已取消")