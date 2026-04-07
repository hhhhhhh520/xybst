"""
测试用例 - 单元测试和集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch

# 添加项目路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.rag_retriever import RAGRetriever, RetrievalResult
from services.agent_workflow import (
    IntentClassifier, SlotFiller, AgentWorkflow, IntentType, DialogueState
)
from services.knowledge_base import DocumentProcessor, ChunkingStrategy


# ========== RAG检索模块测试 ==========

class TestRAGRetriever:
    """RAG检索器测试"""

    @pytest.fixture
    def retriever(self):
        return RAGRetriever()

    def test_rrf_fusion(self, retriever):
        """测试RRF融合算法"""
        # 准备测试数据
        vector_results = [
            RetrievalResult(content="doc1", metadata={}, score=0.9, source="vector"),
            RetrievalResult(content="doc2", metadata={}, score=0.8, source="vector"),
            RetrievalResult(content="doc3", metadata={}, score=0.7, source="vector"),
        ]

        keyword_results = [
            RetrievalResult(content="doc2", metadata={}, score=0.95, source="keyword"),
            RetrievalResult(content="doc4", metadata={}, score=0.85, source="keyword"),
        ]

        # 执行融合
        fused = retriever.rrf_fusion(vector_results, keyword_results, k=60)

        # 验证结果
        assert len(fused) <= 5  # 默认返回top5
        assert fused[0].content == "doc2"  # doc2在两个列表中都出现，应该排第一

    def test_rrf_fusion_empty(self, retriever):
        """测试RRF融合 - 空输入"""
        result = retriever.rrf_fusion([], [], k=60)
        assert result == []


# ========== Agent工作流测试 ==========

class TestIntentClassifier:
    """意图分类器测试"""

    def test_classify_knowledge_qa(self):
        """测试知识问答意图识别"""
        queries = [
            "图书馆几点开门？",
            "奖学金怎么申请？",
            "培养方案是什么？",
        ]

        for query in queries:
            intent, confidence = IntentClassifier.classify(query)
            assert intent == IntentType.KNOWLEDGE_QA
            assert confidence > 0.5

    def test_classify_personal_query(self):
        """测试个人查询意图识别"""
        queries = [
            "我的课表是什么？",
            "查询我的成绩",
            "我有多少学分？",
        ]

        for query in queries:
            intent, confidence = IntentClassifier.classify(query)
            assert intent == IntentType.PERSONAL_QUERY

    def test_classify_chitchat(self):
        """测试闲聊意图识别"""
        queries = [
            "你好",
            "谢谢",
            "再见",
        ]

        for query in queries:
            intent, confidence = IntentClassifier.classify(query)
            assert intent == IntentType.CHITCHAT

    def test_classify_unknown(self):
        """测试未知意图"""
        intent, confidence = IntentClassifier.classify("xyz123")
        assert intent == IntentType.UNKNOWN
        assert confidence < 0.5


class TestSlotFiller:
    """槽位填充器测试"""

    def test_extract_semester(self):
        """测试学期信息提取"""
        query = "我想查2024-2025-1学期的成绩"
        slots = SlotFiller.extract_slots(query, IntentType.PERSONAL_QUERY)

        assert "semester" in slots
        assert "2024-2025-1" in slots["semester"]

    def test_extract_query_type_schedule(self):
        """测试查询类型提取 - 课表"""
        query = "我的课表是什么？"
        slots = SlotFiller.extract_slots(query, IntentType.PERSONAL_QUERY)

        assert slots.get("query_type") == "schedule"

    def test_extract_query_type_grades(self):
        """测试查询类型提取 - 成绩"""
        query = "查询我的成绩"
        slots = SlotFiller.extract_slots(query, IntentType.PERSONAL_QUERY)

        assert slots.get("query_type") == "grades"

    def test_check_missing_slots(self):
        """测试缺失槽位检查"""
        filled_slots = {"query_type": "schedule"}
        missing = SlotFiller.check_missing_slots(
            IntentType.PERSONAL_QUERY,
            filled_slots
        )

        assert "semester" in missing


class TestAgentWorkflow:
    """Agent工作流测试"""

    @pytest.fixture
    def workflow(self):
        return AgentWorkflow()

    @pytest.mark.asyncio
    async def test_get_or_create_session(self, workflow):
        """测试会话创建"""
        session = workflow.get_or_create_session("test_session", "test_user")

        assert session.session_id == "test_session"
        assert session.user_id == "test_user"
        assert session.intent == IntentType.UNKNOWN

        # 再次获取应该返回同一个会话
        session2 = workflow.get_or_create_session("test_session", "test_user")
        assert session is session2

    @pytest.mark.asyncio
    async def test_handle_chitchat(self, workflow):
        """测试闲聊处理"""
        state = DialogueState(session_id="test", user_id="test")
        response = await workflow._handle_chitchat("你好", state)

        assert "你好" in response["answer"] or "Hello" in response["answer"]
        assert response["type"] == "chitchat"


# ========== 文档处理测试 ==========

class TestDocumentProcessor:
    """文档处理器测试"""

    def test_clean_text(self):
        """测试文本清洗"""
        dirty_text = "  Hello   World  \n\n  \t  "
        cleaned = DocumentProcessor.clean_text(dirty_text)

        assert cleaned == "Hello World"

    def test_clean_text_with_null(self):
        """测试文本清洗 - 去除空字符"""
        text_with_null = "Hello\x00World"
        cleaned = DocumentProcessor.clean_text(text_with_null)

        assert "\x00" not in cleaned


class TestChunkingStrategy:
    """分块策略测试"""

    def test_create_splitter(self):
        """测试分割器创建"""
        splitter = ChunkingStrategy.create_splitter(chunk_size=100, chunk_overlap=20)

        assert splitter._chunk_size == 100
        assert splitter._chunk_overlap == 20

    def test_split_document_default(self):
        """测试默认分块"""
        content = "这是一段测试文本。" * 50  # 生成较长文本
        metadata = {"title": "测试文档"}

        chunks = ChunkingStrategy.split_document(content, metadata, doc_type="default")

        assert len(chunks) > 0
        assert all(isinstance(c, type(chunks[0])) for c in chunks)
        assert all("chunk_index" in c.metadata for c in chunks)

    def test_split_document_faq(self):
        """测试FAQ文档分块 - 应该保持完整"""
        content = "Q: 问题\nA: 答案"
        metadata = {"title": "FAQ"}

        chunks = ChunkingStrategy.split_document(content, metadata, doc_type="faq")

        assert len(chunks) == 1
        assert chunks[0].page_content == content


# ========== 集成测试 ==========

@pytest.mark.asyncio
async def test_full_chat_flow():
    """测试完整对话流程"""
    workflow = AgentWorkflow()

    # 模拟知识问答
    response = await workflow.process(
        query="图书馆几点开门？",
        session_id="test_session",
        user_id="test_user"
    )

    assert "answer" in response
    assert "type" in response


@pytest.mark.asyncio
async def test_personal_query_without_auth():
    """测试未认证的个人查询"""
    workflow = AgentWorkflow()

    response = await workflow.process(
        query="我的成绩怎么样？",
        session_id="test_session2",
        user_id="test_user2",
        user_info=None
    )

    assert response["type"] == "auth_required"
    assert "绑定" in response["answer"]


# ========== 性能测试 ==========

@pytest.mark.benchmark
class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_intent_classification_speed(self):
        """测试意图分类速度"""
        import time

        query = "图书馆几点开门？"
        start = time.time()

        for _ in range(100):
            IntentClassifier.classify(query)

        elapsed = time.time() - start
        assert elapsed < 1.0  # 100次分类应该在1秒内完成


# ========== 测试数据 ==========

@pytest.fixture
def sample_documents():
    """提供测试文档"""
    return [
        {
            "content": "图书馆开放时间为周一至周五7:00-22:00，周末8:00-21:00",
            "metadata": {"title": "图书馆开放时间", "source": "图书馆"}
        },
        {
            "content": "国家奖学金申请条件：成绩排名专业前10%，无挂科记录",
            "metadata": {"title": "奖学金评定办法", "source": "学工处"}
        },
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
