"""
文档分块模块 - 智能分块策略实现
"""
import re
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass

from services.bm25 import Document
from core.logger import logger


@dataclass
class ChunkResult:
    """分块结果"""
    content: str
    metadata: Dict[str, Any]


class MarkdownChunker:
    """Markdown智能分块器"""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        """
        初始化Markdown分块器

        Args:
            chunk_size: 目标块大小（字符数）
            chunk_overlap: 块之间重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, content: str, metadata: dict) -> List[Document]:
        """
        按Markdown标题结构分块

        - 按 ## 和 ### 标题分割
        - 保护表格完整性（不拆分表格）
        - 保持列表完整性
        - 添加header_path元数据

        Args:
            content: Markdown文档内容
            metadata: 文档元数据

        Returns:
            分块后的Document列表
        """
        # 首先按二级和三级标题分割
        sections = self._split_by_headers(content)

        documents = []
        header_path = []

        for section in sections:
            header_level, header_text, section_content = section

            # 更新header路径
            if header_level == 2:
                header_path = [header_text] if header_text else []
            elif header_level == 3 and header_path:
                if len(header_path) >= 2:
                    header_path = header_path[:1]
                if header_text:
                    header_path.append(header_text)

            # 如果section太大，进一步分割
            sub_chunks = self._split_large_section(section_content)

            for i, chunk_content in enumerate(sub_chunks):
                if not chunk_content.strip():
                    continue

                # 计算chunk_id
                chunk_hash = hashlib.md5(
                    f"{metadata.get('title', '')}:{header_text}:{i}:{chunk_content[:50]}".encode()
                ).hexdigest()[:8]

                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_id': chunk_hash,
                    'chunk_index': i,
                    'chunk_total': len(sub_chunks),
                    'header_path': '/'.join(header_path) if header_path else '',
                    'section_title': header_text,
                    'chunk_type': 'markdown'
                })

                documents.append(Document(
                    page_content=chunk_content.strip(),
                    metadata=chunk_metadata
                ))

        # 如果没有有效的分块，返回整个文档作为一个块
        if not documents:
            chunk_hash = hashlib.md5(
                f"{metadata.get('title', '')}:{content[:50]}".encode()
            ).hexdigest()[:8]

            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_id': chunk_hash,
                'chunk_index': 0,
                'chunk_total': 1,
                'header_path': '',
                'section_title': metadata.get('title', ''),
                'chunk_type': 'markdown'
            })

            documents.append(Document(
                page_content=content.strip(),
                metadata=chunk_metadata
            ))

        # 更新chunk_total为实际总数
        total = len(documents)
        for doc in documents:
            doc.metadata['chunk_total'] = total

        logger.debug(f"Markdown分块完成: {metadata.get('title', '')} -> {total} 块")
        return documents

    def _split_by_headers(self, content: str) -> List[tuple]:
        """
        按标题分割文档

        Returns:
            [(header_level, header_text, content), ...]
        """
        sections = []
        lines = content.split('\n')

        current_level = 0
        current_header = ''
        current_content = []

        for line in lines:
            # 检测二级标题
            if line.startswith('## ') and not line.startswith('### '):
                # 保存之前的section
                if current_content:
                    sections.append((current_level, current_header, '\n'.join(current_content)))

                current_level = 2
                current_header = line[3:].strip()
                current_content = []

            # 检测三级标题
            elif line.startswith('### '):
                # 保存之前的section
                if current_content:
                    sections.append((current_level, current_header, '\n'.join(current_content)))

                current_level = 3
                current_header = line[4:].strip()
                current_content = []

            else:
                current_content.append(line)

        # 保存最后一个section
        if current_content:
            sections.append((current_level, current_header, '\n'.join(current_content)))

        # 如果没有标题，返回整个文档作为第0级
        if not sections:
            sections.append((0, '', content))

        return sections

    def _split_large_section(self, content: str) -> List[str]:
        """
        分割过大的section

        保护表格和列表完整性
        """
        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_length = 0
        in_table = False
        in_list = False

        for line in lines:
            # 检测表格
            if '|' in line and line.strip().startswith('|'):
                in_table = True
            elif in_table and not line.strip().startswith('|') and line.strip():
                in_table = False

            # 检测列表
            list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s', line)
            if list_match:
                in_list = True
            elif in_list and line.strip() and not list_match:
                in_list = False

            line_length = len(line) + 1  # +1 for newline

            # 如果在表格或列表中，不分割
            if in_table or in_list:
                current_chunk.append(line)
                current_length += line_length
                continue

            # 检查是否需要分割
            if current_length + line_length > self.chunk_size and current_chunk:
                # 保存当前块
                chunks.append('\n'.join(current_chunk))

                # 开始新块，包含overlap
                if self.chunk_overlap > 0 and len(current_chunk) > 0:
                    overlap_lines = self._get_overlap_lines(current_chunk)
                    current_chunk = overlap_lines
                    current_length = sum(len(l) + 1 for l in overlap_lines)
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(line)
            current_length += line_length

        # 保存最后一块
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks if chunks else [content]

    def _get_overlap_lines(self, lines: List[str]) -> List[str]:
        """获取重叠行"""
        overlap_chars = 0
        overlap_lines = []

        for line in reversed(lines):
            if overlap_chars + len(line) > self.chunk_overlap:
                break
            overlap_lines.insert(0, line)
            overlap_chars += len(line) + 1

        return overlap_lines


class FAQChunker:
    """FAQ文档分块器 - 按问答对分割"""

    def chunk(self, content: str, metadata: dict) -> List[Document]:
        """
        按Q:/A:或### Q格式分割问答对
        每个问答对作为一个完整块

        Args:
            content: FAQ文档内容
            metadata: 文档元数据

        Returns:
            分块后的Document列表
        """
        qa_pairs = self._extract_qa_pairs(content)

        if not qa_pairs:
            # 如果没有检测到问答对，返回整个文档
            logger.debug(f"未检测到FAQ格式，返回整体: {metadata.get('title', '')}")
            chunk_hash = hashlib.md5(
                f"{metadata.get('title', '')}:{content[:50]}".encode()
            ).hexdigest()[:8]

            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_id': chunk_hash,
                'chunk_index': 0,
                'chunk_total': 1,
                'qa_index': 0,
                'chunk_type': 'faq'
            })

            return [Document(page_content=content.strip(), metadata=chunk_metadata)]

        documents = []
        total = len(qa_pairs)

        for i, (question, answer) in enumerate(qa_pairs):
            # 组合问答对
            qa_content = f"Q: {question}\n\nA: {answer}"

            # 提取问题关键词作为标识
            question_key = question[:30].replace('\n', ' ')

            chunk_hash = hashlib.md5(
                f"{metadata.get('title', '')}:Q{i}:{question_key}".encode()
            ).hexdigest()[:8]

            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_id': chunk_hash,
                'chunk_index': i,
                'chunk_total': total,
                'qa_index': i,
                'question': question[:100],  # 保存问题摘要
                'chunk_type': 'faq'
            })

            documents.append(Document(
                page_content=qa_content,
                metadata=chunk_metadata
            ))

        logger.debug(f"FAQ分块完成: {metadata.get('title', '')} -> {total} 个问答对")
        return documents

    def _extract_qa_pairs(self, content: str) -> List[tuple]:
        """
        提取问答对

        Returns:
            [(question, answer), ...]
        """
        qa_pairs = []

        # 首先尝试按 "Q:" 或 "问题：" 分割
        lines = content.strip().split('\n')
        current_q = None
        current_a = []

        for line in lines:
            line_stripped = line.strip()

            # 检测问题行 (Q:, 问题:, ### Q等)
            q_match = re.match(r'^(?:#{1,3}\s*)?[Qq问][：:]\s*(.+)$', line_stripped)
            if q_match:
                # 保存之前的问答对
                if current_q and current_a:
                    qa_pairs.append((current_q, ' '.join(current_a).strip()))

                current_q = q_match.group(1).strip()
                current_a = []
                continue

            # 检测答案行 (A:, 答:, ### A等)
            a_match = re.match(r'^(?:#{1,3}\s*)?[Aa答][：:]\s*(.+)$', line_stripped)
            if a_match and current_q:
                # 如果已经有答案内容，保存之前的问答对
                if current_a:
                    qa_pairs.append((current_q, ' '.join(current_a).strip()))
                    current_a = []
                current_a.append(a_match.group(1).strip())
                continue

            # 检测数字序号问题 (1. 问题, 1、问题等)
            num_q_match = re.match(r'^\d+[.、]\s*(.+)$', line_stripped)
            if num_q_match and not current_q:
                # 这可能是一个新的问题
                current_q = num_q_match.group(1).strip()
                current_a = []
                continue

            # 普通行，添加到当前答案
            if current_q and line_stripped:
                current_a.append(line_stripped)

        # 保存最后一个问答对
        if current_q and current_a:
            qa_pairs.append((current_q, ' '.join(current_a).strip()))

        return qa_pairs


class ChunkingManager:
    """分块管理器"""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        """
        初始化分块管理器

        Args:
            chunk_size: 默认块大小
            chunk_overlap: 默认块重叠大小
        """
        self.markdown_chunker = MarkdownChunker(chunk_size, chunk_overlap)
        self.faq_chunker = FAQChunker()

    def chunk_document(
        self,
        content: str,
        metadata: dict,
        doc_type: str = 'policy'
    ) -> List[Document]:
        """
        根据文档类型选择合适的分块器

        Args:
            content: 文档内容
            metadata: 文档元数据
            doc_type: 文档类型
                - 'policy': 政策文档（使用Markdown分块器）
                - 'faq': FAQ文档（使用FAQ分块器）
                - 'process': 流程文档（使用Markdown分块器）
                - 'guide': 指南文档（使用Markdown分块器）

        Returns:
            分块后的Document列表
        """
        # 根据文档类型选择分块器
        if doc_type == 'faq':
            return self.faq_chunker.chunk(content, metadata)
        else:
            # policy, process, guide等都使用Markdown分块器
            return self.markdown_chunker.chunk(content, metadata)

    def get_chunker_info(self) -> Dict[str, Any]:
        """获取分块器信息"""
        return {
            'markdown_chunker': {
                'chunk_size': self.markdown_chunker.chunk_size,
                'chunk_overlap': self.markdown_chunker.chunk_overlap
            },
            'faq_chunker': {
                'type': 'qa_pair_based'
            }
        }
