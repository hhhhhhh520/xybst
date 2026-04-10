"""
API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any

from models.schemas import ChatRequest, ChatResponse, UserBindRequest, DocumentUpload
from services.agent_workflow import workflow
from services.knowledge_base import KnowledgeBaseService
from services.answer_cache import get_cache
from core.logger import logger

router = APIRouter()
kb_service = KnowledgeBaseService()


# ========== 对话相关 ==========


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口

    - **message**: 用户消息
    - **session_id**: 会话ID
    - **user_id**: 用户ID
    - **user_info**: 用户信息（可选）
    """
    try:
        result = await workflow.process(
            query=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            user_info=request.user_info
        )

        return ChatResponse(
            answer=result.get("answer", ""),
            type=result.get("type", "unknown"),
            sources=result.get("sources"),
            data=result.get("data"),
            cached=result.get("cached")
        )

    except Exception as e:
        logger.error(f"对话处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 知识库管理 ==========


@router.post("/knowledge/documents")
async def add_document(request: DocumentUpload):
    """添加文档到知识库"""
    try:
        doc_id = await kb_service.add_document(
            content=request.content,
            title=request.title,
            source=request.source,
            doc_type=request.doc_type
        )

        return {"success": True, "doc_id": doc_id}

    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/search")
async def search_knowledge(
    query: str,
    top_k: int = 5
):
    """搜索知识库"""
    try:
        from services.rag_retriever import retriever
        results = await retriever.retrieve(query, top_k=top_k)

        return {
            "query": query,
            "results": [
                {
                    "content": r.content[:200] + "...",
                    "metadata": r.metadata,
                    "score": r.score
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/stats")
async def knowledge_stats():
    """知识库统计"""
    try:
        stats = await kb_service.get_stats()
        return stats

    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 用户相关 ==========


@router.post("/user/bind")
async def bind_user(request: UserBindRequest):
    """绑定用户身份"""
    # 实际项目中应调用教务系统API验证
    # 这里返回模拟成功
    return {
        "success": True,
        "message": "绑定成功",
        "user_info": {
            "user_id": request.user_id,
            "student_id": request.student_id,
            "name": "张三",
            "college": "计算机学院",
            "major": "计算机科学与技术",
            "grade": "大三",
            "is_bound": True
        }
    }


@router.get("/user/info/{user_id}")
async def get_user_info(user_id: str):
    """获取用户信息"""
    # 返回模拟数据
    return {
        "user_id": user_id,
        "is_bound": False,
        "name": None,
        "college": None,
        "major": None
    }


# ========== 系统相关 ==========

@router.get("/system/config")
async def get_config():
    """获取系统配置"""
    from core.config import settings

    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL
    }


@router.get("/system/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


# ========== 缓存管理 ==========


@router.get("/cache/stats")
async def cache_stats():
    """
    获取缓存统计信息

    返回：
    - total_requests: 总请求数
    - cache_hits: 缓存命中次数
    - cache_misses: 缓存未命中次数
    - hit_rate: 命中率
    - current_size: 当前缓存大小
    - max_size: 最大缓存容量
    """
    try:
        cache = get_cache()
        stats = cache.get_stats()
        return stats

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """
    清空缓存

    返回：
    - success: 操作是否成功
    - cleared_count: 清除的缓存条目数
    """
    try:
        cache = get_cache()
        cleared_count = cache.clear()
        logger.info(f"缓存已清空，清除条目数: {cleared_count}")

        return {
            "success": True,
            "cleared_count": cleared_count,
            "message": f"已清空 {cleared_count} 条缓存"
        }

    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/entries")
async def list_cache_entries(limit: int = 100):
    """
    获取缓存条目列表（用于调试）

    参数：
    - limit: 返回条目数量限制（默认100）

    返回：
    - entries: 缓存条目列表
    """
    try:
        cache = get_cache()
        entries = cache.get_entries(limit=limit)

        return {
            "count": len(entries),
            "entries": entries
        }

    except Exception as e:
        logger.error(f"获取缓存条目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
