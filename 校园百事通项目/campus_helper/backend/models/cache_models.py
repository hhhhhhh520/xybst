"""
缓存数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    query: str
    answer: str
    sources: List[dict] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    intent: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hit_count: int = 0

    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class CacheStats:
    """缓存统计"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
