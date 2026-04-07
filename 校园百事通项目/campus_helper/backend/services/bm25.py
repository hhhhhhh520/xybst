"""
BM25检索模块 - 基于jieba分词的中文BM25实现
"""
import math
import jieba
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import Counter


@dataclass
class Document:
    """文档数据类"""
    page_content: str
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    metadata: Dict[str, Any]
    score: float


class BM25:
    """
    BM25检索算法实现

    参数说明:
    - k1: 控制词频饱和度的参数，通常1.2-2.0
    - b: 控制文档长度归一化的参数，通常0.75
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[List[str]] = []  # 分词后的文档列表
        self.doc_objects: List[Document] = []  # 原始文档对象
        self.doc_lengths: List[int] = []  # 文档长度列表
        self.avg_doc_length: float = 0  # 平均文档长度
        self.doc_count: int = 0  # 文档总数
        self.doc_freqs: Dict[str, int] = Counter()  # 词的文档频率
        self.idf_cache: Dict[str, float] = {}  # IDF缓存

        # 停用词表
        self.stop_words = set([
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '什么', '他', '她', '它', '们', '这个', '那个', '怎么',
            '吗', '呢', '啊', '吧', '呀', '哦', '嗯', '哈', '哪', '些', '个', '能', '可以'
        ])

    def _tokenize(self, text: str) -> List[str]:
        """
        分词并过滤停用词

        Args:
            text: 输入文本

        Returns:
            分词后的词列表
        """
        # 使用jieba精确模式分词
        words = jieba.lcut(text, cut_all=False)
        # 过滤停用词和单字符
        return [w.lower() for w in words if w.strip() and w.lower() not in self.stop_words and len(w) > 1]

    def add_documents(self, documents: List[Document]):
        """
        添加文档到索引

        Args:
            documents: 文档列表
        """
        for doc in documents:
            tokens = self._tokenize(doc.page_content)
            self.documents.append(tokens)
            self.doc_objects.append(doc)
            self.doc_lengths.append(len(tokens))

            # 更新文档频率
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1

        self.doc_count = len(self.documents)
        if self.doc_count > 0:
            self.avg_doc_length = sum(self.doc_lengths) / self.doc_count

        # 清除IDF缓存
        self.idf_cache = {}

    def _get_idf(self, term: str) -> float:
        """
        计算词的IDF值

        Args:
            term: 词

        Returns:
            IDF值
        """
        if term in self.idf_cache:
            return self.idf_cache[term]

        doc_freq = self.doc_freqs.get(term, 0)
        if doc_freq == 0:
            idf = 0
        else:
            # BM25 IDF公式
            idf = math.log((self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1)

        self.idf_cache[term] = idf
        return idf

    def _score_document(self, query_tokens: List[str], doc_tokens: List[str], doc_length: int) -> float:
        """
        计算文档与查询的相关性分数

        Args:
            query_tokens: 查询词列表
            doc_tokens: 文档词列表
            doc_length: 文档长度

        Returns:
            BM25分数
        """
        score = 0.0
        doc_term_freqs = Counter(doc_tokens)

        for term in query_tokens:
            if term not in doc_term_freqs:
                continue

            tf = doc_term_freqs[term]
            idf = self._get_idf(term)

            # BM25评分公式
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            score += idf * numerator / denominator

        return score

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            检索结果列表
        """
        if not self.documents:
            return []

        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # 计算所有文档的分数
        scored_docs = []
        for i, (doc_tokens, doc_length) in enumerate(zip(self.documents, self.doc_lengths)):
            score = self._score_document(query_tokens, doc_tokens, doc_length)
            if score > 0:
                scored_docs.append((i, score))

        # 按分数排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 返回TopK结果
        results = []
        for idx, score in scored_docs[:top_k]:
            results.append(SearchResult(
                content=self.doc_objects[idx].page_content,
                metadata=self.doc_objects[idx].metadata,
                score=score
            ))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息

        Returns:
            统计信息字典
        """
        return {
            "doc_count": self.doc_count,
            "avg_doc_length": round(self.avg_doc_length, 2),
            "vocab_size": len(self.doc_freqs),
            "total_terms": sum(self.doc_lengths)
        }
