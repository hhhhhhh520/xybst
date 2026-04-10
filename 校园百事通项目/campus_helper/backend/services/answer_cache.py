"""
答案缓存服务 - LRU缓存实现，支持精确匹配和语义相似度匹配
"""
import hashlib
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

from models.cache_models import CacheEntry, CacheStats
from core.logger import logger


class AnswerCache:
    """
    答案缓存服务

    特性：
    - LRU (Least Recently Used) 淘汰策略
    - 支持精确匹配和语义相似度匹配
    - 线程安全
    - 缓存过期机制
    - 统计功能
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        similarity_threshold: float = 0.95,
        stats_enabled: bool = True
    ):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存过期时间（秒）
            similarity_threshold: 语义相似度阈值（0-1）
            stats_enabled: 是否启用统计
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._similarity_threshold = similarity_threshold
        self._stats_enabled = stats_enabled
        self._stats = CacheStats()
        self._lock = threading.RLock()

        logger.info(
            f"[缓存服务] 初始化完成 - 最大容量: {max_size}, "
            f"TTL: {ttl_seconds}秒, 相似度阈值: {similarity_threshold}"
        )

    def _generate_key(self, query: str, intent: str = "") -> str:
        """
        生成缓存键

        Args:
            query: 查询文本
            intent: 意图类型

        Returns:
            缓存键（MD5哈希）
        """
        content = f"{query.strip().lower()}:{intent}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度分数（0-1）
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _evict_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的条目数
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]
            self._stats.evictions += 1

        if expired_keys:
            logger.debug(f"[缓存] 清理过期条目: {len(expired_keys)}个")

        return len(expired_keys)

    def _evict_lru(self) -> None:
        """
        LRU淘汰策略 - 移除最久未使用的条目
        """
        while len(self._cache) >= self._max_size:
            # OrderedDict的popitem(last=False)移除最早的条目
            oldest_key, _ = self._cache.popitem(last=False)
            self._stats.evictions += 1
            logger.debug(f"[缓存] LRU淘汰: {oldest_key[:8]}...")

    def get(
        self,
        query: str,
        embedding: Optional[List[float]] = None,
        intent: str = ""
    ) -> Optional[CacheEntry]:
        """
        查询缓存

        Args:
            query: 查询文本
            embedding: 查询向量（用于语义相似度匹配）
            intent: 意图类型

        Returns:
            缓存条目，未命中返回None
        """
        with self._lock:
            # 更新统计
            self._stats.total_requests += 1

            # 1. 尝试精确匹配
            key = self._generate_key(query, intent)

            if key in self._cache:
                entry = self._cache[key]

                # 检查是否过期
                if entry.is_expired():
                    del self._cache[key]
                    self._stats.cache_misses += 1
                    logger.debug(f"[缓存] 精确命中但已过期: {key[:8]}...")
                    return None

                # LRU更新：移动到末尾（最近使用）
                self._cache.move_to_end(key)
                entry.hit_count += 1
                self._stats.cache_hits += 1
                logger.info(f"[缓存] 精确命中: {key[:8]}... (命中次数: {entry.hit_count})")
                return entry

            # 2. 尝试语义相似度匹配
            if embedding:
                best_match: Tuple[Optional[str], float] = (None, 0.0)

                for cache_key, entry in self._cache.items():
                    # 检查意图是否匹配
                    if intent and entry.intent and entry.intent != intent:
                        continue

                    # 检查是否过期
                    if entry.is_expired():
                        continue

                    # 计算相似度
                    if entry.embedding:
                        similarity = self._cosine_similarity(embedding, entry.embedding)
                        if similarity > best_match[1]:
                            best_match = (cache_key, similarity)

                # 检查最佳匹配是否满足阈值
                if best_match[0] and best_match[1] >= self._similarity_threshold:
                    entry = self._cache[best_match[0]]
                    self._cache.move_to_end(best_match[0])
                    entry.hit_count += 1
                    self._stats.cache_hits += 1
                    logger.info(
                        f"[缓存] 语义匹配命中: 相似度={best_match[1]:.3f}, "
                        f"原查询='{entry.query[:20]}...'"
                    )
                    return entry

            # 未命中
            self._stats.cache_misses += 1
            logger.debug(f"[缓存] 未命中: '{query[:30]}...'")
            return None

    def set(
        self,
        query: str,
        answer: str,
        sources: List[dict] = None,
        embedding: Optional[List[float]] = None,
        intent: str = ""
    ) -> CacheEntry:
        """
        存入缓存

        Args:
            query: 查询文本
            answer: 答案内容
            sources: 来源列表
            embedding: 查询向量
            intent: 意图类型

        Returns:
            创建的缓存条目
        """
        with self._lock:
            # 清理过期缓存
            self._evict_expired()

            # LRU淘汰
            self._evict_lru()

            # 创建缓存条目
            key = self._generate_key(query, intent)
            now = datetime.now()
            expires_at = now + timedelta(seconds=self._ttl_seconds)

            entry = CacheEntry(
                key=key,
                query=query,
                answer=answer,
                sources=sources or [],
                embedding=embedding,
                intent=intent,
                created_at=now,
                expires_at=expires_at,
                hit_count=0
            )

            # 存入缓存
            self._cache[key] = entry
            logger.info(
                f"[缓存] 存入成功: '{query[:30]}...' "
                f"(当前缓存数: {len(self._cache)}/{self._max_size})"
            )

            return entry

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            return {
                "enabled": True,
                "total_requests": self._stats.total_requests,
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "evictions": self._stats.evictions,
                "hit_rate": round(self._stats.hit_rate, 4),
                "current_size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl_seconds,
                "similarity_threshold": self._similarity_threshold
            }

    def clear(self) -> int:
        """
        清空缓存

        Returns:
            清除的条目数
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"[缓存] 已清空，清除条目数: {count}")
            return count

    def remove(self, query: str, intent: str = "") -> bool:
        """
        移除指定缓存

        Args:
            query: 查询文本
            intent: 意图类型

        Returns:
            是否成功移除
        """
        with self._lock:
            key = self._generate_key(query, intent)
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"[缓存] 移除成功: {key[:8]}...")
                return True
            return False

    def get_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取缓存条目列表（用于调试）

        Args:
            limit: 返回条目数量限制

        Returns:
            缓存条目列表
        """
        with self._lock:
            entries = []
            for key, entry in list(self._cache.items())[-limit:]:
                entries.append({
                    "key": key[:16] + "...",
                    "query": entry.query[:50] + "..." if len(entry.query) > 50 else entry.query,
                    "intent": entry.intent,
                    "hit_count": entry.hit_count,
                    "created_at": entry.created_at.isoformat(),
                    "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                    "is_expired": entry.is_expired()
                })
            return entries


# 全局缓存实例（延迟初始化）
_cache_instance: Optional[AnswerCache] = None


def get_cache() -> AnswerCache:
    """
    获取全局缓存实例（单例模式）

    Returns:
        AnswerCache实例
    """
    global _cache_instance

    if _cache_instance is None:
        from core.config import settings

        # 从配置读取缓存参数
        cache_config = getattr(settings, 'cache', None)

        if cache_config:
            _cache_instance = AnswerCache(
                max_size=getattr(cache_config, 'max_size', 1000),
                ttl_seconds=getattr(cache_config, 'ttl_seconds', 3600),
                similarity_threshold=getattr(cache_config, 'similarity_threshold', 0.95),
                stats_enabled=getattr(cache_config, 'stats_enabled', True)
            )
        else:
            # 使用默认配置
            _cache_instance = AnswerCache()

    return _cache_instance


def init_cache(
    max_size: int = 1000,
    ttl_seconds: int = 3600,
    similarity_threshold: float = 0.95,
    stats_enabled: bool = True
) -> AnswerCache:
    """
    初始化全局缓存实例

    Args:
        max_size: 最大缓存条目数
        ttl_seconds: 缓存过期时间（秒）
        similarity_threshold: 语义相似度阈值
        stats_enabled: 是否启用统计

    Returns:
        AnswerCache实例
    """
    global _cache_instance
    _cache_instance = AnswerCache(
        max_size=max_size,
        ttl_seconds=ttl_seconds,
        similarity_threshold=similarity_threshold,
        stats_enabled=stats_enabled
    )
    return _cache_instance
