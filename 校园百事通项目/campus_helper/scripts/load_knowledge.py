# -*- coding: utf-8 -*-
"""
加载知识库文档到RAG检索系统
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.rag_retriever import retriever, Document


async def load_knowledge_base():
    """加载知识库文档"""
    kb_path = Path(__file__).parent.parent / "data" / "knowledge_base"

    print("=" * 60)
    print("加载知识库文档")
    print("=" * 60)

    # 初始化检索器
    print("\n[1] 初始化RAG检索器...")
    await retriever.initialize()
    print("    [OK] 初始化完成")

    # 收集所有文档
    print("\n[2] 扫描知识库目录...")
    documents = []

    for md_file in kb_path.rglob("*.md"):
        # 跳过chroma_db目录
        if "chroma_db" in str(md_file):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            if content.strip():
                # 获取相对路径作为分类
                rel_path = md_file.relative_to(kb_path)
                category = rel_path.parts[0] if len(rel_path.parts) > 1 else "其他"

                documents.append(Document(
                    page_content=content,
                    metadata={
                        "title": md_file.stem,
                        "category": category,
                        "source": str(md_file)
                    }
                ))
        except Exception as e:
            print(f"    [WARN] 读取失败: {md_file.name} - {e}")

    print(f"    [OK] 扫描到 {len(documents)} 个文档")

    # 添加文档到检索器
    print("\n[3] 加载文档到RAG检索器...")
    if documents:
        # 分批加载，每批10个
        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            await retriever.add_documents(batch)
            print(f"    已加载 {min(i+batch_size, len(documents))}/{len(documents)} 个文档")

    # 获取统计信息
    stats = retriever.get_stats()
    print(f"\n[4] 加载完成")
    print(f"    向量库文档数: {stats['vector_count']}")
    print(f"    BM25文档数: {stats['bm25_stats']['doc_count']}")

    # 测试检索
    print("\n[5] 测试检索...")
    test_queries = [
        "图书馆几点开门",
        "奖学金怎么申请",
        "如何办理在读证明",
        "宿舍熄灯时间",
    ]

    for query in test_queries:
        results = await retriever.retrieve(query, top_k=2)
        print(f"\n    查询: [{query}]")
        if results:
            for r in results:
                print(f"      - {r.metadata.get('title', 'N/A')} (分数: {r.score:.4f})")
        else:
            print("      无结果")

    print("\n" + "=" * 60)
    print("知识库加载完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(load_knowledge_base())
