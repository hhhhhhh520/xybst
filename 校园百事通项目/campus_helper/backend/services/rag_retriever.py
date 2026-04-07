"""
RAG检索服务 - 向量检索 + BM25关键词检索 + RRF融合
使用 bge-large-zh 向量模型 + Chroma向量数据库
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import logger
from models.schemas import RetrievalResult
from services.bm25 import BM25, Document, SearchResult

# 设置Hugging Face镜像源（国内用户）
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')


class EmbeddingService:
    """Embedding服务 - 使用bge-large-zh"""

    def __init__(self):
        self.model = None
        self.cache_dir = Path(settings.EMBEDDING_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _download_model(self):
        """下载模型到本地缓存目录"""
        from huggingface_hub import snapshot_download

        model_name = settings.EMBEDDING_MODEL
        local_dir = self.cache_dir / model_name.replace("/", "_")

        if not local_dir.exists():
            logger.info(f"[下载] 首次运行，正在下载模型 {model_name}...")
            logger.info(f"[缓存] 模型将保存到: {local_dir}")
            try:
                snapshot_download(
                    repo_id=model_name,
                    local_dir=str(local_dir)
                )
                logger.info("[完成] 模型下载完成")
            except Exception as e:
                logger.error(f"[错误] 模型下载失败: {e}")
                logger.info("[提示] 请检查网络连接，或手动下载模型到: " + str(local_dir))
                raise
        else:
            logger.info(f"[缓存] 使用本地缓存模型: {local_dir}")

        return str(local_dir)

    def initialize(self):
        """初始化Embedding模型"""
        if self.model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            # 获取模型路径（本地缓存或下载）
            model_path = self._download_model()

            logger.info("[加载] 正在加载Embedding模型...")
            self.model = SentenceTransformer(
                model_path,
                device=settings.EMBEDDING_DEVICE
            )
            logger.info(f"[完成] Embedding模型加载完成，维度: {self.model.get_sentence_embedding_dimension()}")

        except Exception as e:
            logger.error(f"[错误] Embedding模型加载失败: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        if self.model is None:
            self.initialize()
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入多个文档"""
        if self.model is None:
            self.initialize()
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


class VectorStore:
    """向量存储 - 使用Chroma"""

    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_service = None
        self.persist_dir = Path(settings.CHROMA_PERSIST_DIR) / "chroma_db"

    def initialize(self, embedding_service: EmbeddingService):
        """初始化向量存储"""
        if self.collection is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.embedding_service = embedding_service

            logger.info(f"[初始化] Chroma向量数据库: {self.persist_dir}")

            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )

            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )

            logger.info(f"[完成] Chroma初始化完成，当前文档数: {self.collection.count()}")

        except Exception as e:
            logger.error(f"[错误] Chroma初始化失败: {e}")
            raise

    def add_documents(self, documents: List[Document]):
        """添加文档到向量库"""
        if self.collection is None:
            raise RuntimeError("VectorStore未初始化")

        if not documents:
            return

        # 生成embedding
        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding_service.embed_documents(texts)

        # 生成ID
        ids = [f"doc_{i}_{hash(doc.page_content) % 1000000}" for i, doc in enumerate(documents)]

        # 添加到Chroma
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[doc.metadata for doc in documents]
        )

        logger.info(f"[完成] 添加 {len(documents)} 个文档到向量库")

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """向量检索"""
        if self.collection is None:
            return []

        if self.collection.count() == 0:
            return []

        # 生成查询向量
        query_embedding = self.embedding_service.embed_query(query)

        # 检索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # 转换结果
        retrieval_results = []
        if results and results["documents"]:
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                # Chroma返回的是距离，转换为相似度
                similarity = 1 - distance
                retrieval_results.append(RetrievalResult(
                    content=doc,
                    metadata=metadata,
                    score=similarity,
                    source="vector"
                ))

        return retrieval_results

    def count(self) -> int:
        """获取文档数量"""
        if self.collection is None:
            return 0
        return self.collection.count()


class RAGRetriever:
    """
    RAG检索器 - 向量检索 + BM25 + RRF融合
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.bm25 = BM25(
            k1=settings.BM25_K1,
            b=settings.BM25_B
        )
        self.documents: List[Document] = []  # 内存中的文档副本
        self.is_initialized = False

    async def initialize(self):
        """初始化检索器"""
        if self.is_initialized:
            return

        logger.info("[初始化] RAG检索器...")

        try:
            # 初始化Embedding服务
            self.embedding_service.initialize()

            # 初始化向量存储
            self.vector_store.initialize(self.embedding_service)

            self.is_initialized = True
            logger.info("[完成] RAG检索器初始化完成")

        except Exception as e:
            logger.error(f"[错误] RAG检索器初始化失败: {e}")
            raise

    async def vector_search(self, query: str, top_k: int = None) -> List[RetrievalResult]:
        """
        向量检索

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        if not self.is_initialized:
            await self.initialize()

        top_k = top_k or settings.RAG_TOP_K
        return self.vector_store.search(query, top_k=top_k)

    async def keyword_search(self, query: str, top_k: int = None) -> List[RetrievalResult]:
        """
        BM25关键词检索

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        if not self.is_initialized:
            await self.initialize()

        top_k = top_k or settings.RAG_TOP_K
        bm25_results = self.bm25.search(query, top_k=top_k)

        return [
            RetrievalResult(
                content=r.content,
                metadata=r.metadata,
                score=r.score,
                source="keyword"
            )
            for r in bm25_results
        ]

    def rrf_fusion(
        self,
        vector_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult],
        k: int = 60
    ) -> List[RetrievalResult]:
        """
        RRF (Reciprocal Rank Fusion) 结果融合

        Args:
            vector_results: 向量检索结果
            keyword_results: 关键词检索结果
            k: RRF参数

        Returns:
            融合后的结果
        """
        doc_scores: Dict[int, float] = {}
        doc_contents: Dict[int, str] = {}
        doc_metadata: Dict[int, Dict] = {}

        # 处理向量检索结果
        for rank, result in enumerate(vector_results):
            doc_id = hash(result.content)
            score = 1.0 / (k + rank + 1)

            if doc_id in doc_scores:
                doc_scores[doc_id] += score
            else:
                doc_scores[doc_id] = score
                doc_contents[doc_id] = result.content
                doc_metadata[doc_id] = result.metadata

        # 处理关键词检索结果
        for rank, result in enumerate(keyword_results):
            doc_id = hash(result.content)
            score = 1.0 / (k + rank + 1)

            if doc_id in doc_scores:
                doc_scores[doc_id] += score
            else:
                doc_scores[doc_id] = score
                doc_contents[doc_id] = result.content
                doc_metadata[doc_id] = result.metadata

        # 按分数排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果
        fusion_results = []
        for doc_id, score in sorted_docs[:settings.RAG_TOP_K]:
            fusion_results.append(RetrievalResult(
                content=doc_contents[doc_id],
                metadata=doc_metadata[doc_id],
                score=score,
                source="fusion"
            ))

        logger.debug(f"RRF融合: 向量结果{len(vector_results)}条, 关键词结果{len(keyword_results)}条, 融合后{len(fusion_results)}条")
        return fusion_results

    async def retrieve(
        self,
        query: str,
        top_k: int = None,
        use_vector: bool = True,
        use_keyword: bool = True
    ) -> List[RetrievalResult]:
        """
        综合检索

        Args:
            query: 查询文本
            top_k: 返回数量
            use_vector: 是否使用向量检索
            use_keyword: 是否使用关键词检索

        Returns:
            检索结果列表
        """
        if not self.is_initialized:
            await self.initialize()

        logger.info(f"[检索] 执行检索: {query[:50]}...")

        # 执行检索
        vector_results = []
        keyword_results = []

        if use_vector:
            vector_results = await self.vector_search(query, top_k=top_k)

        if use_keyword:
            keyword_results = await self.keyword_search(query, top_k=top_k)

        # 结果融合
        if use_vector and use_keyword:
            results = self.rrf_fusion(vector_results, keyword_results)
        elif use_vector:
            results = vector_results[:top_k or settings.RAG_TOP_K]
        else:
            results = keyword_results[:top_k or settings.RAG_TOP_K]

        # 过滤低分结果
        results = [r for r in results if r.score >= settings.RAG_SIMILARITY_THRESHOLD]

        logger.info(f"[完成] 检索完成，返回 {len(results)} 条结果")
        return results

    async def add_documents(self, documents: List[Document]):
        """
        添加文档到知识库

        Args:
            documents: 文档列表
        """
        if not self.is_initialized:
            await self.initialize()

        if not documents:
            return

        # 添加到向量存储
        self.vector_store.add_documents(documents)

        # 添加到BM25索引
        self.bm25.add_documents(documents)

        # 保存到内存
        self.documents.extend(documents)

        logger.info(f"[完成] 成功添加 {len(documents)} 个文档片段")

    def get_stats(self) -> Dict[str, Any]:
        """获取检索器统计信息"""
        return {
            "vector_count": self.vector_store.count(),
            "bm25_stats": self.bm25.get_stats(),
            "is_initialized": self.is_initialized
        }


# 全局检索器实例
retriever = RAGRetriever()
