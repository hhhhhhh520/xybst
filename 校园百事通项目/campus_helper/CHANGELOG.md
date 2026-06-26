# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2] - 2026-06-26

### Fixed

- **LLM 意图分类完全失效**
  - `agent_workflow.py` 中 `_llm_classify()` 调用已删除的 `_call_zhipu()` 方法
  - `43ea2e5` 将 `_call_zhipu` 合并进 `_call_llm` 时漏改了此处，`hasattr` 检查永远返回 False
  - 改为调用 `_dispatch()` 统一分发，适配所有 LLM provider

- **前端 sources 标题未转义**
  - `index.html` 中 `sources.map(s => s.title)` 直接拼接 innerHTML，复用 `escapeHtml()` 转义

### Added

- 新增 `test_llm_classify_parses_json` 测试，覆盖 LLM 意图分类路径（此前 0 覆盖）

## [1.2.1] - 2026-06-25

### Fixed

- **BM25 测试构造函数不匹配**
  - 测试中 `BM25(docs)` 改为 `BM25()` + `add_documents(docs)`，修正 API 用法
  - 修正断言使用 `SearchResult.content` 而非 `Document.page_content`
  - 修正无匹配测试断言（BM25 始终返回 top_k 结果，检查分数而非数量）

- **LLM 跨提供商分发 Bug**
  - 新增 `_dispatch()` 统一分发方法，替代各方法硬编码的 provider 调用
  - `generate_guide()`、`rewrite_query()`、`rewrite_query_with_context()` 改为调用 `_dispatch()`
  - `generate_answer_stream()` 加 provider 分支，支持 openai 流式 + 其他 provider 降级

- **知识库删除功能崩溃**
  - `VectorStore` 新增 `delete_by_metadata()` 方法，通过 ChromaDB `where` 过滤删除向量
  - `RAGRetriever` 新增 `delete_documents_by_metadata()` 方法，同步删除向量和内存文档
  - `KnowledgeBaseService.delete_document()` 重写为调用 `retriever.delete_documents_by_metadata()`
  - 原代码引用不存在的 `retriever.vectors` 属性导致 `AttributeError`

- **实例生命周期混乱**
  - `knowledge_base.py` 末尾新增模块级单例 `kb_service`
  - `main.py` lifespan 和 `routes.py` 统一导入同一实例，消除重复初始化和文档重复加载

- **会话内存泄漏**
  - `AgentWorkflow` 新增 `_session_last_active` 字典追踪会话活跃时间
  - 新增 `_cleanup_stale_sessions()` 方法，每 100 次访问清理超过 1 小时的过期会话

- **前端 XSS 漏洞**
  - 新增 `escapeHtml()` 函数，`formatContent()` 先转义 HTML 特殊字符再渲染 markdown
  - 防止用户输入或 LLM 输出中的 `<script>` 标签被执行

- **文档 ID 跨重启不稳定**
  - `VectorStore.add_documents()` 的文档 ID 从 `hash(content) % 1000000` 改为 `hashlib.sha256(content)[:12]`
  - 解决 Python `hash()` 每次启动随机化导致的 ChromaDB 孤儿条目问题

### Changed

- **系统提示词提取为常量**
  - `LLMService._SYSTEM_PROMPT` 类常量，`generate_answer()` 和 `generate_answer_stream()` 共用
  - 消除 44 行提示词的代码重复

- **前端 API 地址改为相对路径**
  - `API_BASE` 从 `http://localhost:8000/api` 改为 `/api`，支持同源部署

### Removed

- **清理未使用的 Pydantic 模型**
  - 删除 `Feedback`、`FeedbackRequest`、`KnowledgeStats`、`UsageStats`、`SystemStatus`

### Fixed (dependencies)

- **requirements.txt 清理**
  - 删除重复的 `httpx==0.25.2` 条目

### ⚠️ 升级注意

从 v1.2.0 升级到 v1.2.1 后，由于文档 ID 生成算法变更，需要**清空并重建** ChromaDB 索引：

```bash
# 删除旧的向量数据库
rm -rf data/chroma_db/

# 重新导入知识库
python scripts/process_documents.py
```

## [1.2.0] - 2026-04-11

### Added

- **上下文查询重写功能**
  - 新增 `rewrite_query_with_context()` 方法，根据对话历史重写用户输入
  - 自动将简短回答（如"本科"）转换为完整查询（如"本科生奖学金申请"）
  - 提升多轮对话的上下文理解能力
  - 仅对15字符以内的简短输入进行重写，避免误改完整问题

### Changed

- **Agent工作流优化**
  - 在意图识别之前增加查询重写步骤
  - 改善追问场景下的对话连贯性

## [1.1.0] - 2026-04-10

### Added

- **YAML分离配置方案**
  - 新增 `settings.yaml` 主配置文件
  - 新增 `settings.local.yaml` 本地覆盖配置
  - 支持环境变量注入和敏感信息隔离

- **文档智能分块功能**
  - 实现 `MarkdownChunker` 用于Markdown文档分块
  - 实现 `FAQChunker` 用于FAQ格式文档分块
  - 支持自定义分块大小和重叠长度

- **答案缓存功能**
  - 基于LRU算法的缓存淘汰机制
  - 语义相似度匹配缓存键
  - 缓存命中率统计功能
  - 可配置缓存大小和过期时间

- **Embedding模型预热**
  - 应用启动时自动预热Embedding模型
  - 减少首次查询延迟

- **多LLM提供商支持**
  - DeepSeek API集成
  - 智谱AI（GLM）集成
  - OpenAI API集成
  - Anthropic Claude集成
  - Ollama本地模型集成
  - 统一的LLM接口抽象层

- **缓存管理API**
  - `GET /api/cache/stats` 获取缓存统计信息
  - `POST /api/cache/clear` 清空缓存

### Changed

- **意图分类器优化**
  - 扩展关键词词典覆盖范围
  - 提升意图识别准确率

- **fallback响应优化**
  - 无匹配答案时建议咨询辅导员
  - 提供更友好的引导信息

### Fixed

- **numpy 2.0与chromadb兼容性问题**
  - 锁定numpy版本为兼容版本
  - 解决向量数据库初始化失败问题

- **依赖版本冲突问题**
  - 统一依赖版本管理
  - 修复pip依赖解析冲突

---

## [1.0.0] - 2026-03-15

### Added

- 项目初始化发布
- 基础问答功能
- 意图分类模块
- RAG检索增强生成
- ChromaDB向量数据库集成
- FastAPI后端服务
- Web前端界面

---

## 版本说明

- **[1.1.0]**: 功能增强版本，新增配置分离、智能分块、缓存系统、多LLM支持
- **[1.0.0]**: 首个正式发布版本

---

## 升级指南

### 从 v1.0.0 升级到 v1.1.0

1. 更新依赖：
   ```bash
   pip install -r requirements.txt --upgrade
   ```

2. 配置迁移：
   - 将原有配置迁移至 `settings.yaml`
   - 创建 `settings.local.yaml` 存放敏感信息（API密钥等）
   - 将 `settings.local.yaml` 添加到 `.gitignore`

3. 缓存功能启用：
   - 缓存功能默认开启
   - 可在 `settings.yaml` 中配置缓存大小和过期时间

4. 多LLM配置：
   - 在 `settings.local.yaml` 中配置所需LLM提供商的API密钥
   - 设置 `llm.provider` 选择默认提供商
