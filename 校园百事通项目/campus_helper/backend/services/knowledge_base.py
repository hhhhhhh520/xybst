"""
知识库服务 - 文档处理、分块、索引管理
"""
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from services.rag_retriever import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.chunker import ChunkingManager

from core.config import settings
from core.logger import logger
from services.rag_retriever import retriever


class DocumentProcessor:
    """文档处理器"""

    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text',
        '.md': 'markdown',
        '.pdf': 'pdf',
        '.docx': 'word',
        '.doc': 'word',
    }

    @classmethod
    def load_document(cls, file_path: str) -> str:
        """
        加载文档内容

        Args:
            file_path: 文件路径

        Returns:
            文档内容
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}")

        doc_type = cls.SUPPORTED_EXTENSIONS[ext]

        try:
            if doc_type == 'text' or doc_type == 'markdown':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            elif doc_type == 'pdf':
                return cls._load_pdf(file_path)

            elif doc_type == 'word':
                return cls._load_word(file_path)

        except Exception as e:
            logger.error(f"加载文档失败 {file_path}: {e}")
            raise

    @classmethod
    def _load_pdf(cls, file_path: str) -> str:
        """加载PDF文档"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            logger.error("请安装pypdf: pip install pypdf")
            raise

    @classmethod
    def _load_word(cls, file_path: str) -> str:
        """加载Word文档"""
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except ImportError:
            logger.error("请安装python-docx: pip install python-docx")
            raise

    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        清洗文本

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        # 去除多余空白
        text = ' '.join(text.split())

        # 去除特殊字符
        text = text.replace('\x00', '')

        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        return text.strip()


class ChunkingStrategy:
    """分块策略"""

    @staticmethod
    def create_splitter(
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> RecursiveCharacterTextSplitter:
        """
        创建文本分割器

        Args:
            chunk_size: 块大小
            chunk_overlap: 重叠大小

        Returns:
            文本分割器
        """
        chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP

        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "；", " ", ""],
            length_function=len,
        )

    @classmethod
    def split_document(
        cls,
        content: str,
        metadata: Dict[str, Any],
        doc_type: str = "default"
    ) -> List[Document]:
        """
        分割文档

        Args:
            content: 文档内容
            metadata: 文档元数据
            doc_type: 文档类型

        Returns:
            分割后的文档块
        """
        # 根据文档类型选择分块参数
        if doc_type == "faq":
            # FAQ保持完整，不分块
            return [Document(page_content=content, metadata=metadata)]

        elif doc_type == "process":
            # 流程文档，较小块
            splitter = cls.create_splitter(chunk_size=200, chunk_overlap=20)

        else:
            # 默认策略
            splitter = cls.create_splitter()

        # 分割文档
        chunks = splitter.split_text(content)

        # 为每个块创建Document对象
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "chunk_total": len(chunks),
            })
            documents.append(Document(
                page_content=chunk,
                metadata=chunk_metadata
            ))

        return documents


class KnowledgeBaseService:
    """知识库服务"""

    def __init__(self):
        self.processor = DocumentProcessor()
        self.chunk_manager = ChunkingManager()
        self.is_initialized = False

    async def initialize(self):
        """初始化知识库服务"""
        if self.is_initialized:
            return

        logger.info("初始化知识库服务...")

        # 确保目录存在
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

        # 初始化检索器
        await retriever.initialize()

        # 自动加载知识库文档
        await self._load_knowledge_base()

        self.is_initialized = True
        logger.info("知识库服务初始化完成")

    async def _load_knowledge_base(self):
        """从知识库目录加载文档"""
        kb_dir = Path(settings.CHROMA_PERSIST_DIR)

        # 如果是相对路径，转换为绝对路径
        if not kb_dir.is_absolute():
            # 相对于项目根目录
            project_root = Path(__file__).parent.parent.parent
            kb_dir = project_root / settings.CHROMA_PERSIST_DIR

        if not kb_dir.exists():
            logger.warning(f"知识库目录不存在: {kb_dir}")
            return

        logger.info(f"正在加载知识库: {kb_dir}")

        # 支持的文件扩展名
        supported_exts = ['.md', '.txt']

        doc_count = 0

        # 遍历所有子目录
        for category_dir in kb_dir.iterdir():
            if not category_dir.is_dir():
                continue

            category_name = category_dir.name

            # 遍历目录中的文件
            for ext in supported_exts:
                for file_path in category_dir.glob(f'*{ext}'):
                    try:
                        # 读取文件内容
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # 构建元数据
                        metadata = {
                            'title': file_path.stem,
                            'source': category_name,
                            'doc_type': 'policy',
                            'category': category_name,
                            'file_path': str(file_path)
                        }

                        # 使用分块器进行智能分块
                        chunk_manager = ChunkingManager()
                        chunks = chunk_manager.chunk_document(content, metadata, 'policy')

                        # 添加分块后的文档到检索器
                        await retriever.add_documents(chunks)
                        doc_count += len(chunks)

                    except Exception as e:
                        logger.error(f"加载文档失败 {file_path}: {e}")

        logger.info(f"知识库加载完成，共 {doc_count} 个文档块")

    async def add_document(
        self,
        content: str,
        title: str,
        source: str,
        doc_type: str = "policy",
        **kwargs
    ) -> str:
        """
        添加文档到知识库

        Args:
            content: 文档内容
            title: 文档标题
            source: 来源部门
            doc_type: 文档类型
            **kwargs: 其他元数据

        Returns:
            文档ID
        """
        if not self.is_initialized:
            await self.initialize()

        # 生成文档ID
        doc_id = hashlib.md5(f"{title}:{source}".encode()).hexdigest()[:12]

        # 清洗文本
        cleaned_content = self.processor.clean_text(content)

        # 构建元数据
        metadata = {
            "doc_id": doc_id,
            "title": title,
            "source": source,
            "doc_type": doc_type,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }

        # 分块
        chunks = self.chunk_manager.chunk_document(
            cleaned_content,
            metadata,
            doc_type
        )

        # 添加到向量数据库
        await retriever.add_documents(chunks)

        logger.info(f"✅ 文档已添加到知识库: {title} ({len(chunks)} 块)")

        return doc_id

    async def add_document_from_file(
        self,
        file_path: str,
        title: str = None,
        source: str = "未知来源",
        doc_type: str = "policy"
    ) -> str:
        """
        从文件添加文档

        Args:
            file_path: 文件路径
            title: 文档标题（默认为文件名）
            source: 来源部门
            doc_type: 文档类型

        Returns:
            文档ID
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 使用文件名作为默认标题
        if title is None:
            title = path.stem

        # 加载文档内容
        content = self.processor.load_document(file_path)

        # 添加到知识库
        return await self.add_document(
            content=content,
            title=title,
            source=source,
            doc_type=doc_type,
            file_path=str(file_path)
        )

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            # 统计文档数量
            total_docs = len(retriever.documents)

            # 按来源统计
            sources = {}
            doc_types = {}

            for doc in retriever.documents:
                metadata = doc.metadata or {}
                source = metadata.get('source', '未知')
                doc_type = metadata.get('doc_type', '未知')

                sources[source] = sources.get(source, 0) + 1
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            return {
                "total_documents": total_docs,
                "sources": sources,
                "doc_types": doc_types,
                "embedding_model": settings.EMBEDDING_MODEL,
                "persist_directory": settings.CHROMA_PERSIST_DIR
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "total_documents": 0,
                "error": str(e)
            }

    async def delete_document(self, doc_id: str) -> bool:
        """
        删除文档

        Args:
            doc_id: 文档ID

        Returns:
            是否成功
        """
        try:
            # 过滤掉要删除的文档
            original_count = len(retriever.documents)
            retriever.documents = [
                doc for doc in retriever.documents
                if doc.metadata.get('doc_id') != doc_id
            ]

            # 同时删除对应的向量
            if len(retriever.vectors) == original_count:
                # 保持向量和文档的对应关系
                new_vectors = []
                new_documents = []
                for i, doc in enumerate(retriever.documents):
                    if doc.metadata.get('doc_id') != doc_id:
                        new_documents.append(doc)
                        if i < len(retriever.vectors):
                            new_vectors.append(retriever.vectors[i])
                retriever.documents = new_documents
                retriever.vectors = new_vectors

            deleted = len(retriever.documents) < original_count
            if deleted:
                logger.info(f"✅ 文档已删除: {doc_id}")
            return deleted

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_dict: 过滤条件

        Returns:
            搜索结果
        """
        from services.rag_retriever import RetrievalResult

        results = await retriever.retrieve(query, top_k=top_k)

        return [
            {
                "content": r.content,
                "metadata": r.metadata,
                "score": r.score,
                "source": r.source
            }
            for r in results
        ]
