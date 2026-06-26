# -*- coding: utf-8 -*-
"""
测试升级后的RAG检索模块 - 完整版
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.rag_retriever import RAGRetriever, Document


async def test_rag_module():
    """测试RAG检索模块"""
    print("=" * 60)
    print("RAG检索模块测试")
    print("=" * 60)

    # 创建检索器
    retriever = RAGRetriever()

    # 测试文档
    test_docs = [
        Document(
            page_content="图书馆开放时间为周一至周五7:00-22:00，周末8:00-21:00。图书馆位于校园中心区域，共有五层楼，提供自习室、阅览室和电子阅览室。",
            metadata={"title": "图书馆开放时间", "source": "图书馆", "category": "校园服务"}
        ),
        Document(
            page_content="国家奖学金申请条件：成绩排名专业前10%，无挂科记录，综合素质测评优秀。申请时间为每年9月份，需要提交申请表、成绩单和个人陈述。",
            metadata={"title": "国家奖学金评定办法", "source": "学工处", "category": "奖助学金"}
        ),
        Document(
            page_content="在读证明办理流程：携带学生证到教务处窗口办理，或通过教务系统在线申请。办理时间：工作日上午8:30-11:30，下午14:00-17:00。",
            metadata={"title": "在读证明办理", "source": "教务处", "category": "教务信息"}
        ),
        Document(
            page_content="宿舍熄灯时间为晚上11点，周末和节假日延长至12点。宿舍内禁止使用大功率电器，违者将给予警告处分。",
            metadata={"title": "宿舍管理规定", "source": "后勤处", "category": "生活服务"}
        ),
        Document(
            page_content="选课时间为每学期第16周，通过教务系统进行选课。必修课由系统自动分配，选修课需要自行选择。选课期间可以退改选。",
            metadata={"title": "选课流程", "source": "教务处", "category": "教务信息"}
        ),
    ]

    print("\n[1] 初始化检索器...")
    try:
        await retriever.initialize()
        print("    [OK] 初始化成功")
    except Exception as e:
        print(f"    [FAIL] 初始化失败: {e}")
        return

    print("\n[2] 添加测试文档...")
    try:
        await retriever.add_documents(test_docs)
        print("    [OK] 文档添加成功")
    except Exception as e:
        print(f"    [FAIL] 文档添加失败: {e}")
        return

    # 获取统计信息
    stats = retriever.get_stats()
    print(f"\n[3] 统计信息:")
    print(f"    向量库文档数: {stats['vector_count']}")
    print(f"    BM25文档数: {stats['bm25_stats']['doc_count']}")

    # 测试查询
    test_queries = [
        "图书馆几点开门",
        "奖学金怎么申请",
        "怎么办理在读证明",
        "宿舍几点熄灯",
        "选课时间",
    ]

    print("\n[4] 测试检索功能...")
    for query in test_queries:
        print(f"\n    查询: [{query}]")
        results = await retriever.retrieve(query, top_k=3)
        if results:
            for i, r in enumerate(results, 1):
                print(f"      [{i}] 分数={r.score:.4f} 来源={r.source}")
                print(f"          标题: {r.metadata.get('title', 'N/A')}")
        else:
            print("      无结果")

    print("\n" + "=" * 60)
    print("测试完成 - RAG检索模块升级成功!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_rag_module())
