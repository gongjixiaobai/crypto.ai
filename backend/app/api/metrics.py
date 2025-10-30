from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.trading import Metrics as MetricsModel
from datetime import datetime
import time
import threading
from typing import List, Dict, Any, Optional
import hashlib
import json

# 添加线程安全的内存缓存
class ThreadSafeMetricsCache:
    def __init__(self):
        self.cache = None
        self.expiry = 0
        self.ttl = 15  # 增加缓存时间到15秒，减少数据库查询频率
        self._lock = threading.Lock()
        self.data_hash = None  # 用于检测数据是否真正发生变化
    
    def get(self):
        with self._lock:
            if self.cache and time.time() < self.expiry:
                return self.cache
            return None
    
    def set(self, data):
        with self._lock:
            # 计算数据的哈希值以检测变化
            data_str = json.dumps(data, sort_keys=True, default=str)
            new_hash = hashlib.md5(data_str.encode()).hexdigest()
            
            # 只有在数据真正发生变化时才更新缓存
            if new_hash != self.data_hash:
                self.cache = data
                self.data_hash = new_hash
            
            self.expiry = time.time() + self.ttl

metrics_cache = ThreadSafeMetricsCache()

router = APIRouter()

@router.get("/")
async def get_metrics(db: Session = Depends(get_db)):
    """获取指标数据"""
    # 检查缓存
    cached_data = metrics_cache.get()
    if cached_data:
        return cached_data
    
    try:
        # 优化查询：只获取最新的记录，并限制返回的字段
        latest_metric = db.query(MetricsModel) \
                         .filter(MetricsModel.model == "Deepseek") \
                         .order_by(MetricsModel.created_at.desc()) \
                         .first()
        
        if not latest_metric:
            result = {
                "success": True,
                "data": {
                    "metrics": [],
                    "totalCount": 0,
                    "model": "Deepseek",
                    "name": "20-seconds-metrics",
                },
            }
            metrics_cache.set(result)
            return result
        
        # 优化处理指标数据
        metrics_data: List[Dict[str, Any]] = []
        if latest_metric.metrics and isinstance(latest_metric.metrics, list):
            # 限制返回的指标数据数量，只返回最新的150条记录以提高性能
            metrics_list = latest_metric.metrics
            if len(metrics_list) > 150:
                metrics_list = metrics_list[-150:]  # 只取最新的150条
                
            # 批量处理数据以提高性能
            for metric in metrics_list:
                if isinstance(metric, dict):
                    # 使用get方法安全访问嵌套字段
                    account_info = metric.get("accountInformationAndPerformance", {})
                    metrics_data.append({
                        "totalCashValue": account_info.get("totalCashValue", 0),
                        "currentTotalReturn": account_info.get("currentTotalReturn", 0),
                        "createdAt": metric.get("createdAt", ""),
                    })
        
        result = {
            "success": True,
            "data": {
                "metrics": metrics_data,
                "totalCount": len(metrics_data),
                "model": latest_metric.model,
                "name": latest_metric.name,
                "createdAt": latest_metric.created_at.isoformat() if latest_metric.created_at else "",
                "updatedAt": latest_metric.updated_at.isoformat() if latest_metric.updated_at else "",
            },
        }
        
        # 缓存结果
        metrics_cache.set(result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))