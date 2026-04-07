#!/usr/bin/env python3
"""
文档处理脚本 - 批量处理校园文档并导入知识库

使用方法:
    python scripts/process_documents.py --input ./data/raw_docs --output ./data/processed

"""
import os
import sys
import json
import argparse
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.knowledge_base import KnowledgeBaseService
from backend.core.logger import logger


# 文档来源映射
SOURCE_MAPPING = {
    "jwc": "教务处",
    "xgc": "学工处",
    "hq": "后勤处",
    "tsg": "图书馆",
    "xy": "校医院",
    "jiuye": "就业中心",
}

# 文档类型映射
TYPE_MAPPING = {
    "policy": "政策文件",
    "process": "办事流程",
    "notice": "通知公告",
    "faq": "常见问题",
}


def parse_filename(filename: str) -> dict:
    """
    从文件名解析元数据

    文件名格式: [来源]_[类型]_[标题].扩展名
    示例: jwc_policy_奖学金评定办法.pdf

    Args:
        filename: 文件名

    Returns:
        解析后的元数据
    """
    path = Path(filename)
    name = path.stem  # 不含扩展名的文件名
    parts = name.split("_", 2)  # 最多分割成3部分

    metadata = {
        "source": "未知来源",
        "doc_type": "policy",
        "title": name,
    }

    if len(parts) >= 1 and parts[0] in SOURCE_MAPPING:
        metadata["source"] = SOURCE_MAPPING[parts[0]]

    if len(parts) >= 2 and parts[1] in TYPE_MAPPING:
        metadata["doc_type"] = parts[1]

    if len(parts) >= 3:
        metadata["title"] = parts[2]

    return metadata


async def process_single_file(
    file_path: Path,
    kb_service: KnowledgeBaseService,
    output_dir: Path
) -> dict:
    """
    处理单个文件

    Args:
        file_path: 文件路径
        kb_service: 知识库服务
        output_dir: 输出目录

    Returns:
        处理结果
    """
    result = {
        "file": str(file_path),
        "status": "failed",
        "doc_id": None,
        "error": None
    }

    try:
        # 解析文件名获取元数据
        metadata = parse_filename(file_path.name)

        logger.info(f"📄 处理文件: {file_path.name}")
        logger.info(f"   标题: {metadata['title']}")
        logger.info(f"   来源: {metadata['source']}")
        logger.info(f"   类型: {metadata['doc_type']}")

        # 添加到知识库
        doc_id = await kb_service.add_document_from_file(
            file_path=str(file_path),
            title=metadata["title"],
            source=metadata["source"],
            doc_type=metadata["doc_type"]
        )

        result["status"] = "success"
        result["doc_id"] = doc_id

        logger.info(f"✅ 处理成功: {doc_id}")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ 处理失败: {file_path.name} - {e}")

    return result


async def process_directory(
    input_dir: Path,
    output_dir: Path,
    supported_exts: tuple = ('.txt', '.md', '.pdf', '.docx', '.doc')
) -> list:
    """
    处理目录中的所有文档

    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        supported_exts: 支持的文件扩展名

    Returns:
        处理结果列表
    """
    # 初始化知识库服务
    kb_service = KnowledgeBaseService()
    await kb_service.initialize()

    # 查找所有支持的文件
    files = []
    for ext in supported_exts:
        files.extend(input_dir.glob(f"*{ext}"))
        files.extend(input_dir.glob(f"*{ext.upper()}"))

    if not files:
        logger.warning(f"⚠️ 在 {input_dir} 中没有找到支持的文档")
        return []

    logger.info(f"📁 找到 {len(files)} 个文档待处理")
    logger.info("=" * 50)

    # 处理所有文件
    results = []
    for i, file_path in enumerate(files, 1):
        logger.info(f"\n[{i}/{len(files)}] 处理中...")
        result = await process_single_file(file_path, kb_service, output_dir)
        results.append(result)

    return results


def generate_report(results: list, output_path: Path):
    """
    生成处理报告

    Args:
        results: 处理结果列表
        output_path: 报告输出路径
    """
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    failed = total - success

    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": f"{success/total*100:.1f}%" if total > 0 else "0%"
        },
        "details": results
    }

    # 保存报告
    report_file = output_path / f"process_report_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("\n" + "=" * 50)
    logger.info("📊 处理报告")
    logger.info(f"   总计: {total}")
    logger.info(f"   成功: {success}")
    logger.info(f"   失败: {failed}")
    logger.info(f"   成功率: {report['summary']['success_rate']}")
    logger.info(f"   报告已保存: {report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量处理校园文档并导入知识库"
    )
    parser.add_argument(
        "--input", "-i",
        default="./data/raw_docs",
        help="输入目录（原始文档）"
    )
    parser.add_argument(
        "--output", "-o",
        default="./data/processed",
        help="输出目录（处理报告）"
    )
    parser.add_argument(
        "--env", "-e",
        default=".env",
        help="环境变量文件路径"
    )

    args = parser.parse_args()

    # 确保目录存在
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        logger.error(f"❌ 输入目录不存在: {input_dir}")
        sys.exit(1)

    logger.info("🚀 开始处理文档")
    logger.info(f"   输入目录: {input_dir}")
    logger.info(f"   输出目录: {output_dir}")
    logger.info("=" * 50)

    # 运行异步处理
    results = asyncio.run(process_directory(input_dir, output_dir))

    # 生成报告
    if results:
        generate_report(results, output_dir)
    else:
        logger.warning("⚠️ 没有文档被处理")

    logger.info("\n✨ 处理完成!")


if __name__ == "__main__":
    main()
