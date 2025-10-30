#!/usr/bin/env python3
# 用于检查crypto.ai项目中的数据表记录数

import sys
import os

# 将项目根目录添加到Python路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.trading import Chat, Metric, Pricing, CompletedTrade

def check_table_counts():
    db = SessionLocal()
    try:
        chat_count = db.query(Chat).count()
        metric_count = db.query(Metric).count()
        pricing_count = db.query(Pricing).count()
        completed_trade_count = db.query(CompletedTrade).count()
        
        print(f"Chat 表记录数: {chat_count}")
        print(f"Metric 表记录数: {metric_count}")
        print(f"Pricing 表记录数: {pricing_count}")
        print(f"CompletedTrade 表记录数: {completed_trade_count}")
        print(f"总记录数: {chat_count + metric_count + pricing_count + completed_trade_count}")
    finally:
        db.close()

if __name__ == "__main__":
    check_table_counts()