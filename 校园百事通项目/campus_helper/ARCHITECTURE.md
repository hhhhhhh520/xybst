# 校园百事通系统架构文档

> 本文档描述校园百事通智能服务系统的整体架构设计、核心模块实现及关键技术流程。

## 目录

- [系统架构概览](#系统架构概览)
- [核心模块说明](#核心模块说明)
- [配置加载流程](#配置加载流程)
- [RAG检索流程](#rag检索流程)
- [文档分块策略](#文档分块策略)
- [答案缓存机制](#答案缓存机制)
- [Embedding预热机制](#embedding预热机制)
- [多LLM提供商适配](#多llm提供商适配)

---

## 系统架构概览

```
+------------------------------------------------------------------+
|                          用户交互层                                |
|  +------------------------------------------------------------+  |
|  |                    Frontend (HTML/CSS/JS)                  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
|                          API网关层                                |
|  +------------------------------------------------------------+  |
|  |                    FastAPI Router                          |  |
|  |  - POST /api/chat        对话接口                          |  |
|  |  - POST /api/knowledge/* 知识库管理                        |  |
|  |  - GET  /api/cache/*     缓存管理                          |  |
|  |  - GET  /api/system/*    系统配置                          |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
|                         业务逻辑层                                |
|  +------------------------------------------------------------+  |
|  |                  Agent Workflow Engine                     |  |
|  |  +-------------+  +-------------+  +-------------+         |  |
|  |  | 意图分类器   |  | 槽位填充器  |  | 对话管理器  |         |  |
|  |  | (关键词+LLM)|  |             |  |             |         |  |
|  |  +-------------+  +-------------+  +-------------+         |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+---------------+     +-------------------+     +---------------+
|   LLM服务     |     |    RAG检索服务    |     |   缓存服务    |
| LLMService    |     |   RAGRetriever    |     | AnswerCache   |
|               |     |                   |     |               |
| - DeepSeek    |     | +-------------+   |     | - LRU淘汰    |
| - 智谱AI      |     | | Embedding   |   |     | - 语义匹配   |
| - OpenAI      |     | | Service     |   |     | - TTL过期    |
| - Anthropic   |     | +-------------+   |     |               |
| - Ollama      |     | | VectorStore |   |     |               |
|               |     | +-------------+   |     |               |
|               |     | | BM25检索    |   |     |               |
|               |     | +-------------+   |     |               |
+---------------+     +-------------------+     +---------------+
        |                       |                       |
        |                       v                       |
        |           +-------------------+               |
        |           |   ChromaDB向量库   |               |
        |           +-------------------+               |
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                                v
+------------------------------------------------------------------+
|                          数据存储层                               |
|  +----------------+  +----------------+  +----------------+      |
|  | ChromaDB       |  | 知识库文档     |  | YAML配置文件   |      |
|  | (向量持久化)   |  | (Markdown/TXT)|  | settings.yaml  |      |
|  +----------------+  +----------------+  +----------------+      |
+------------------------------------------------------------------+
```

---

## 核心模块说明

### 1. Config配置模块

**位置**: `config/`, `backend/core/config.py`

配置模块采用分层设计，支持公共配置与私有配置分离。

#### 主要组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `loader.py` | `config/loader.py` | YAML配置加载、深度合并 |
| `config.py` | `backend/core/config.py` | 配置兼容层，提供属性访问 |

#### 配置类结构

```
Settings
├── app: AppConfig              # 应用配置（名称、版本、端口）
├── database: DatabaseConfig    # 数据库配置
├── vector_db: VectorDBConfig   # 向量数据库配置
├── llm: LLMConfig              # LLM配置
│   └── providers: Dict[str, ProviderConfig]  # 多提供商配置
├── embedding: EmbeddingConfig  # Embedding模型配置
├── rag: RAGConfig              # RAG检索配置
├── bm25: BM25Config            # BM25参数配置
├── security: SecurityConfig    # 安全配置
├── logging: LoggingConfig      # 日志配置
└── cache: CacheConfig          # 缓存配置
```

#### 配置加载顺序

```yaml
# settings.yaml - 公共配置（提交到Git）
app:
  name: 校园百事通
  version: 1.0.0

# settings.local.yaml - 私有配置（不提交，包含API密钥）
llm:
  providers:
    deepseek:
      api_key: "your-api-key"
```

---

### 2. Services服务层

**位置**: `backend/services/`

服务层是系统的核心，包含所有业务逻辑实现。

#### 服务模块总览

| 模块 | 类名 | 职责 |
|------|------|------|
| `llm_service.py` | `LLMService` | 多LLM提供商统一调用接口 |
| `rag_retriever.py` | `RAGRetriever` | RAG检索（向量+BM25+RRF融合） |
| `knowledge_base.py` | `KnowledgeBaseService` | 知识库管理、文档处理 |
| `chunker.py` | `ChunkingManager` | 文档智能分块 |
| `bm25.py` | `BM25` | BM25关键词检索算法 |
| `answer_cache.py` | `AnswerCache` | 答案缓存（LRU+语义匹配） |
| `agent_workflow.py` | `AgentWorkflow` | 意图识别、对话管理 |

#### 服务依赖关系

```
AgentWorkflow
    ├── LLMService
    ├── RAGRetriever
    │       ├── EmbeddingService
    │       ├── VectorStore
    │       └── BM25
    └── AnswerCache
```

---

### 3. Models数据层

**位置**: `backend/models/`

| 模块 | 内容 |
|------|------|
| `schemas.py` | API请求/响应模型（ChatRequest, ChatResponse等） |
| `cache_models.py` | 缓存数据模型（CacheEntry, CacheStats） |

---

### 4. API路由层

**位置**: `backend/api/routes.py`

#### API端点设计

```
/api
├── /chat                    [POST]   对话接口
├── /knowledge
│   ├── /documents           [POST]   添加文档
│   ├── /search              [GET]    搜索知识库
│   └── /stats               [GET]    知识库统计
├── /user
│   ├── /bind                [POST]   绑定身份
│   └── /info/{user_id}      [GET]    用户信息
├── /cache
│   ├── /stats               [GET]    缓存统计
│   ├── /entries             [GET]    缓存条目列表
│   └── /clear               [POST]   清空缓存
└── /system
    ├── /config              [GET]    系统配置
    └── /health              [GET]    健康检查
```

---

## 配置加载流程

### YAML配置深度合并

系统采用两层YAML配置文件策略，实现公共配置与私有配置的分离。

```
+------------------+     +----------------------+
| settings.yaml    |     | settings.local.yaml  |
| (公共配置)       |     | (私有配置，含密钥)   |
+------------------+     +----------------------+
        |                          |
        v                          v
+------------------------------------------------+
|              load_yaml_config()                |
|  1. 加载 settings.yaml                         |
|  2. 检查 settings.local.yaml 是否存在          |
|  3. 调用 deep_merge() 合并配置                 |
+------------------------------------------------+
                        |
                        v
+------------------------------------------------+
|              deep_merge(base, override)        |
|                                                |
|  递归合并策略：                                 |
|  - 基础配置中的字典与覆盖配置中的字典深度合并    |
|  - 非字典值直接覆盖                             |
|                                                |
|  示例：                                        |
|  base: {llm: {provider: "zhipu", timeout: 60}} |
|  override: {llm: {provider: "deepseek"}}       |
|  结果: {llm: {provider: "deepseek", timeout: 60}}|
+------------------------------------------------+
                        |
                        v
+------------------------------------------------+
|              Settings.from_dict()              |
|  将配置字典转换为dataclass对象                  |
+------------------------------------------------+
```

### 深度合并算法实现

```python
def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典，override中的值会覆盖base中的值
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 递归合并嵌套字典
            result[key] = deep_merge(result[key], value)
        else:
            # 非字典值直接覆盖
            result[key] = value
    return result
```

---

## RAG检索流程

### 混合检索架构

系统采用**向量检索 + BM25关键词检索 + RRF融合**的混合检索策略。

```
用户查询: "图书馆开放时间"
        |
        v
+------------------------------------------------+
|              RAGRetriever.retrieve()           |
+------------------------------------------------+
        |                       |
        v                       v
+---------------+       +---------------+
|  向量检索      |       |  BM25检索     |
| VectorStore   |       |  BM25         |
| .search()     |       |  .search()    |
+---------------+       +---------------+
        |                       |
        v                       v
+---------------+       +---------------+
| 语义相似度     |       | 关键词匹配    |
| bge-large-zh |       | jieba分词     |
| Cosine距离    |       | TF-IDF加权    |
+---------------+       +---------------+
        |                       |
        +-----------+-----------+
                    |
                    v
+------------------------------------------------+
|              RRF融合 (Reciprocal Rank Fusion) |
|                                                |
|  公式: score(d) = sum(1 / (k + rank(d)))       |
|  默认 k = 60                                   |
|                                                |
|  优点：                                        |
|  - 无需调参                                    |
|  - 对各检索系统的评分尺度不敏感                |
|  - 融合效果稳定                                |
+------------------------------------------------+
                    |
                    v
+------------------------------------------------+
|              结果过滤与排序                     |
|  - 过滤低分结果（threshold = 0.0）             |
|  - 返回Top-K结果                               |
+------------------------------------------------+
```

### 向量检索流程

```
+------------------------------------------------+
|              EmbeddingService                  |
|                                                |
|  模型: BAAI/bge-large-zh-v1.5                  |
|  维度: 1024                                    |
|  设备: CPU (可配置CUDA)                        |
+------------------------------------------------+
        |
        v
+------------------------------------------------+
|              VectorStore (ChromaDB)            |
|                                                |
|  存储配置：                                    |
|  - 持久化目录: ./data/knowledge_base/chroma_db |
|  - Collection: campus_knowledge                |
|  - 距离度量: cosine                            |
|                                                |
|  检索过程：                                    |
|  1. 查询文本 -> Embedding -> 查询向量          |
|  2. ChromaDB ANN检索                           |
|  3. 距离转换为相似度 (1 - distance)            |
+------------------------------------------------+
```

### BM25检索流程

```
+------------------------------------------------+
|              BM25 (基于jieba分词)              |
|                                                |
|  参数：                                        |
|  - k1 = 1.5 (词频饱和参数)                     |
|  - b = 0.75 (文档长度归一化参数)               |
|                                                |
|  预处理：                                      |
|  1. jieba精确模式分词                          |
|  2. 停用词过滤                                 |
|  3. 单字符过滤                                 |
|                                                |
|  评分公式：                                    |
|  score(D,Q) = sum(IDF(qi) * (tf(qi,D) * (k1+1))|
|               / (tf(qi,D) + k1*(1-b+b*|D|/avgdl))|
+------------------------------------------------+
```

### RRF融合算法

```python
def rrf_fusion(
    self,
    vector_results: List[RetrievalResult],
    keyword_results: List[RetrievalResult],
    k: int = 60
) -> List[RetrievalResult]:
    """
    RRF (Reciprocal Rank Fusion) 结果融合

    对每个文档，计算其在两个检索结果列表中的排名倒数之和
    """
    doc_scores: Dict[int, float] = {}

    # 处理向量检索结果
    for rank, result in enumerate(vector_results):
        doc_id = hash(result.content)
        score = 1.0 / (k + rank + 1)
        doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score

    # 处理关键词检索结果
    for rank, result in enumerate(keyword_results):
        doc_id = hash(result.content)
        score = 1.0 / (k + rank + 1)
        doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score

    # 按融合分数排序返回
    return sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
```

---

## 文档分块策略

系统实现两种智能分块策略，针对不同文档类型优化。

### 分块器选择策略

```
文档类型判断
        |
        v
+----------------+     +----------------+
| doc_type=faq   |     | doc_type=policy|
| doc_type=...   |     | process,guide  |
+----------------+     +----------------+
        |                       |
        v                       v
+----------------+     +----------------+
| FAQChunker     |     | MarkdownChunker|
| 问答对分割     |     | 标题结构分割   |
+----------------+     +----------------+
```

### MarkdownChunker (政策文档分块器)

```
+------------------------------------------------+
|              MarkdownChunker                   |
|                                                |
|  目标块大小: 400字符                           |
|  块重叠: 50字符                                |
|                                                |
|  分块策略：                                    |
|  1. 按 ## 和 ### 标题分割                     |
|  2. 维护header_path元数据                      |
|  3. 保护表格完整性（不拆分表格行）             |
|  4. 保护列表完整性                             |
|  5. 大段落递归分割                             |
+------------------------------------------------+

示例：
输入文档：
# 学生管理规定
## 请假制度
### 病假
病假需要提供医院证明...
### 事假
事假需要提前申请...

输出分块：
[
  {
    content: "病假需要提供医院证明...",
    metadata: {
      header_path: "请假制度/病假",
      section_title: "病假",
      chunk_type: "markdown"
    }
  },
  {
    content: "事假需要提前申请...",
    metadata: {
      header_path: "请假制度/事假",
      section_title: "事假",
      chunk_type: "markdown"
    }
  }
]
```

### FAQChunker (问答文档分块器)

```
+------------------------------------------------+
|              FAQChunker                        |
|                                                |
|  分块策略：按问答对分割                         |
|                                                |
|  支持格式：                                    |
|  - Q: / A: 格式                               |
|  - 问题：/ 答：格式                           |
|  - ### Q 格式                                 |
|  - 数字序号格式                                |
+------------------------------------------------+

示例：
输入文档：
Q: 图书馆开放时间是什么？
A: 图书馆周一至周五8:00-22:00开放...

Q: 如何借书？
A: 携带校园卡到图书馆...

输出分块：
[
  {
    content: "Q: 图书馆开放时间是什么？\n\nA: 图书馆周一至周五...",
    metadata: {
      question: "图书馆开放时间是什么？",
      qa_index: 0,
      chunk_type: "faq"
    }
  },
  {
    content: "Q: 如何借书？\n\nA: 携带校园卡...",
    metadata: {
      question: "如何借书？",
      qa_index: 1,
      chunk_type: "faq"
    }
  }
]
```

---

## 答案缓存机制

### 缓存架构

```
+------------------------------------------------+
|              AnswerCache                       |
|                                                |
|  特性：                                        |
|  - LRU (Least Recently Used) 淘汰策略          |
|  - 双模式匹配（精确 + 语义相似度）             |
|  - 线程安全 (RLock)                            |
|  - TTL过期机制                                 |
|  - 统计功能                                    |
|                                                |
|  配置参数：                                    |
|  - max_size: 1000 (最大缓存条目)               |
|  - ttl_seconds: 3600 (过期时间)                |
|  - similarity_threshold: 0.95 (语义匹配阈值)   |
+------------------------------------------------+
```

### 缓存查询流程

```
查询请求
    |
    v
+------------------------------------------------+
|              cache.get(query, embedding)       |
+------------------------------------------------+
    |
    v
+----------------+     是      +----------------+
| 精确匹配?      | ----------> | 返回缓存结果   |
| MD5(query)     |             | 更新LRU位置    |
+----------------+             +----------------+
    | 否
    v
+----------------+     有embedding   +----------------+
| 语义匹配       | ----------------> | 遍历缓存条目  |
|                |                   | 计算余弦相似度|
+----------------+                   +----------------+
    |                                      |
    v                                      v
+----------------+     满足阈值    +----------------+
| 相似度 >= 0.95?| -------------> | 返回语义匹配   |
+----------------+                 | 结果          |
    | 否                           +----------------+
    v
+----------------+
| 缓存未命中     |
| 返回 None      |
+----------------+
```

### LRU淘汰机制

```
+------------------------------------------------+
|              OrderedDict 实现 LRU              |
|                                                |
|  结构：OrderedDict[key, CacheEntry]            |
|                                                |
|  访问时：move_to_end(key) - 移动到末尾         |
|  淘汰时：popitem(last=False) - 移除头部        |
|                                                |
|  示例流程：                                    |
|                                                |
|  初始: [A, B, C, D, E] (容量5)                 |
|  访问C: [A, B, D, E, C]                        |
|  添加F: [B, D, E, C, F] (A被淘汰)              |
+------------------------------------------------+
```

### 缓存数据结构

```python
@dataclass
class CacheEntry:
    """缓存条目"""
    key: str                    # MD5哈希键
    query: str                  # 原始查询
    answer: str                 # 答案内容
    sources: List[dict]         # 来源列表
    embedding: List[float]      # 查询向量（用于语义匹配）
    intent: str                 # 意图类型
    created_at: datetime        # 创建时间
    expires_at: datetime        # 过期时间
    hit_count: int              # 命中次数

@dataclass
class CacheStats:
    """缓存统计"""
    total_requests: int = 0     # 总请求数
    cache_hits: int = 0         # 命中次数
    cache_misses: int = 0       # 未命中次数
    evictions: int = 0          # 淘汰次数

    @property
    def hit_rate(self) -> float:
        """命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
```

---

## Embedding预热机制

### 预热流程

```
+------------------------------------------------+
|              应用启动                          |
+------------------------------------------------+
        |
        v
+------------------------------------------------+
|              KnowledgeBaseService.initialize() |
+------------------------------------------------+
        |
        v
+------------------------------------------------+
|              retriever.initialize()            |
+------------------------------------------------+
        |
        v
+------------------------------------------------+
|              embedding_service.initialize()    |
|                                                |
|  1. 检查本地缓存                               |
|     - 存在: 直接加载                           |
|     - 不存在: 从HuggingFace下载                |
|                                                |
|  2. 加载SentenceTransformer模型                |
|     model = SentenceTransformer(model_path)    |
|                                                |
|  3. 预热模型                                   |
|     _ = model.encode("预热测试")               |
|                                                |
|  预热目的：                                    |
|  - 避免首次查询时的模型加载延迟                |
|  - 预编译计算图                               |
|  - 初始化CUDA（如使用GPU）                     |
+------------------------------------------------+
        |
        v
+------------------------------------------------+
|              vector_store.initialize()         |
|  连接ChromaDB，加载已有向量                    |
+------------------------------------------------+
```

### 模型下载与缓存

```
+------------------------------------------------+
|              HuggingFace镜像配置               |
|                                                |
|  环境变量: HF_ENDPOINT='https://hf-mirror.com' |
|  (国内用户加速)                                |
|                                                |
|  缓存目录: ./models/embedding/                 |
|  模型名称: BAAI_bge-large-zh-v1.5/             |
+------------------------------------------------+
        |
        v
+------------------------------------------------+
|              首次运行检测                      |
|                                                |
|  if not local_dir.exists():                    |
|      snapshot_download(                        |
|          repo_id="BAAI/bge-large-zh-v1.5",     |
|          local_dir=local_dir                   |
|      )                                         |
+------------------------------------------------+
```

---

## 多LLM提供商适配

### 统一接口设计

```
+------------------------------------------------+
|              LLMService                        |
|                                                |
|  统一方法：                                    |
|  - generate_answer(query, context, history)    |
|  - generate_guide(query, context, stage)       |
|  - rewrite_query(query)                        |
+------------------------------------------------+
        |
        | 根据 provider 配置分发
        v
+------------------------------------------------+
|              提供商适配层                      |
|                                                |
|  +-----------+  +-----------+  +-----------+   |
|  | DeepSeek  |  | 智谱AI    |  | OpenAI    |   |
|  |           |  |           |  |           |   |
|  | OpenAI    |  | OpenAI    |  | OpenAI    |   |
|  | 兼容接口  |  | 兼容接口  |  | SDK       |   |
|  +-----------+  +-----------+  +-----------+   |
|                                                |
|  +-----------+  +-----------+                  |
|  | Anthropic |  | Ollama    |                  |
|  |           |  |           |                  |
|  | Anthropic |  | HTTP API  |                  |
|  | SDK       |  |           |                  |
|  +-----------+  +-----------+                  |
+------------------------------------------------+
```

### 提供商配置结构

```yaml
llm:
  provider: deepseek  # 当前使用的提供商

  providers:
    deepseek:
      base_url: https://api.deepseek.com/v1
      model: deepseek-chat
      max_tokens: 1000
      temperature: 0.7
      timeout: 120.0
      api_key: ""

    zhipu:
      base_url: https://open.bigmodel.cn/api/paas/v4/
      model: glm-4-flash
      max_tokens: 1000
      temperature: 0.7
      timeout: 120.0
      api_key: ""

    openai:
      base_url: https://api.openai.com/v1
      model: gpt-3.5-turbo
      max_tokens: 1000
      temperature: 0.7
      api_key: ""

    anthropic:
      model: claude-3-sonnet-20240229
      max_tokens: 1000
      api_key: ""

    local:
      url: http://localhost:11434
      model: qwen:7b
```

### 客户端初始化

```python
class LLMService:
    def __init__(self):
        self.provider = settings.llm.provider

        if self.provider == "openai":
            self.openai_client = AsyncOpenAI(
                api_key=provider_config.api_key,
                base_url=provider_config.base_url
            )

        elif self.provider == "anthropic":
            self.anthropic_client = AsyncAnthropic(
                api_key=provider_config.api_key
            )

        elif self.provider in ["zhipu", "deepseek"]:
            # 智谱AI和DeepSeek使用OpenAI兼容接口
            self.llm_client = AsyncOpenAI(
                api_key=provider_config.api_key,
                base_url=provider_config.base_url,
                timeout=provider_config.timeout
            )
```

### 调用流程

```
generate_answer(query, context, history)
        |
        v
+------------------------------------------------+
|              构建提示词                        |
|  - system_prompt: 角色设定                     |
|  - user_prompt: 上下文 + 问题                  |
+------------------------------------------------+
        |
        v
+------------------------------------------------+
|              路由到对应提供商                  |
|                                                |
|  if provider == "openai":                      |
|      return _call_openai(...)                  |
|  elif provider == "anthropic":                 |
|      return _call_anthropic(...)               |
|  elif provider in ["zhipu", "deepseek"]:       |
|      return _call_llm(...)                     |
|  else:                                         |
|      return _call_local(...)  # Ollama         |
+------------------------------------------------+
```

---

## 技术栈总结

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | FastAPI + Uvicorn |
| 编程语言 | Python 3.12 |
| 向量数据库 | ChromaDB |
| Embedding模型 | BAAI/bge-large-zh-v1.5 (1024维) |
| LLM提供商 | DeepSeek / 智谱AI / OpenAI / Anthropic / Ollama |
| 分词工具 | jieba |
| 配置管理 | YAML + dataclass |
| 缓存实现 | OrderedDict (LRU) |
| 异步HTTP | httpx / AsyncOpenAI |

---

## 性能优化建议

1. **Embedding预热**: 启动时自动预热，避免首次查询延迟
2. **答案缓存**: LRU缓存 + 语义匹配，减少LLM调用
3. **混合检索**: 向量检索 + BM25互补，提高召回率
4. **配置分离**: 公共配置与私有配置分离，便于部署

---

*文档版本: 1.1.0*
*最后更新: 2026年4月*
