# 校园百事通智能服务系统

基于RAG与Agent技术的校园智能问答系统，使用Python + FastAPI + Vue.js实现。

## 功能特性

| 特性 | 描述 |
|------|------|
| 多LLM提供商支持 | DeepSeek、智谱、OpenAI、Anthropic、本地Ollama一键切换 |
| YAML分离配置 | 公共配置与私有配置分离，API密钥安全托管 |
| 文档智能分块 | MarkdownChunker、FAQChunker多种分块策略 |
| 答案缓存 | LRU淘汰、语义匹配、命中率统计 |
| Embedding预热 | 启动时预加载模型，减少首次响应延迟 |
| 混合检索 | 向量检索 + BM25关键词检索 |
| 多轮对话 | 上下文理解和记忆 |

## 技术栈

- **后端**: Python 3.9+, FastAPI, LangChain, ChromaDB
- **前端**: Vue.js 3, Element Plus
- **AI模型**: 多LLM提供商支持
  - DeepSeek (deepseek-chat)
  - 智谱AI (glm-4.7-flash)
  - OpenAI (gpt-3.5-turbo)
  - Anthropic (claude-3-sonnet)
  - 本地模型 Ollama (qwen:7b)
- **向量数据库**: ChromaDB
- **Embedding模型**: BAAI/bge-large-zh-v1.5
- **部署**: Docker + Docker Compose

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

项目采用 **YAML分离配置方案**，将公共配置与私有配置分离：

```bash
# 复制本地配置模板
cp config/settings.yaml config/settings.local.yaml

# 编辑 settings.local.yaml，填写你的 API 密钥
# settings.local.yaml 已加入 .gitignore，不会上传到 GitHub
```

**配置文件说明：**

| 文件 | 用途 | 版本控制 |
|------|------|----------|
| `config/settings.yaml` | 公共配置（模型名称、参数、阈值等） | 提交到Git |
| `config/settings.local.yaml` | 私有配置（API密钥等敏感信息） | 不提交，覆盖公共配置 |

**支持的 LLM 提供商：**

| 提供商 | provider值 | 默认模型 |
|--------|------------|----------|
| DeepSeek | `deepseek` | deepseek-chat |
| 智谱AI | `zhipu` | glm-4.7-flash |
| OpenAI | `openai` | gpt-3.5-turbo |
| Anthropic | `anthropic` | claude-3-sonnet |
| 本地Ollama | `local` | qwen:7b |

**切换LLM提供商示例：**

```yaml
# config/settings.local.yaml
llm:
  provider: deepseek  # 可选: zhipu/openai/anthropic/local

  providers:
    deepseek:
      api_key: "你的DeepSeek API密钥"
```

### 3. 准备知识库

```bash
# 将校园文档放入 data/raw_docs/
# 支持格式: PDF, Word, TXT, Markdown

# 处理文档（自动分块、索引）
python scripts/process_documents.py
```

**文档分块策略：**

| 分块器 | 适用场景 |
|--------|----------|
| MarkdownChunker | Markdown格式文档，按标题层级分块 |
| FAQChunker | FAQ格式文档，问答对提取 |
| RecursiveCharacterTextSplitter | 通用文本，按字符递归分块 |

### 4. 启动服务

```bash
# 启动后端（首次启动会自动预热Embedding模型）
python backend/main.py

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

### 5. 访问系统

- Web界面: http://localhost:5173
- API文档: http://localhost:8000/docs

## 项目结构

```
campus_helper/
├── backend/                  # 后端代码
│   ├── api/                  # API路由
│   ├── core/                 # 核心模块（配置加载等）
│   ├── models/               # 数据模型
│   ├── services/             # 业务逻辑
│   │   ├── agent_workflow.py    # Agent工作流
│   │   ├── answer_cache.py      # 答案缓存服务
│   │   ├── bm25.py              # BM25检索
│   │   ├── chunker.py           # 文档分块器
│   │   ├── knowledge_base.py    # 知识库管理
│   │   ├── llm_service.py       # LLM服务封装
│   │   └── rag_retriever.py     # RAG检索器
│   └── main.py               # 入口文件
├── frontend/                 # 前端代码
│   ├── src/
│   └── package.json
├── data/                     # 数据文件
│   ├── raw_docs/             # 原始文档
│   ├── processed/            # 处理后文档
│   └── knowledge_base/       # 向量数据库
├── config/                   # 配置文件
│   ├── settings.yaml         # 公共配置
│   ├── settings.local.yaml   # 私有配置（需创建）
│   └── loader.py             # 配置加载器
├── models/                   # 本地模型缓存
│   └── embedding/            # Embedding模型
├── scripts/                  # 工具脚本
├── tests/                    # 测试代码
└── logs/                     # 日志文件
```

## 核心功能

### 智能问答

基于RAG的校园政策咨询，结合向量检索与BM25关键词检索，提高召回准确率。

### 知识库管理

- 文档上传、智能分块、自动索引
- 支持MarkdownChunker、FAQChunker等多种分块策略

### 多轮对话

上下文理解和记忆，支持追问和澄清。

### 答案缓存

- LRU淘汰策略，可配置缓存大小
- 语义匹配：相似问题命中缓存
- 命中率统计：监控缓存效果

**缓存配置：**

```yaml
cache:
  enabled: true
  max_size: 1000           # 最大缓存条目数
  ttl_seconds: 3600        # 缓存过期时间
  similarity_threshold: 0.95  # 语义匹配阈值
  stats_enabled: true      # 启用统计
```

### Embedding预热

启动时自动预加载Embedding模型，避免首次请求延迟。

## 相关文档

- [USAGE.md](USAGE.md) - 使用说明
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构文档
- [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - 配置指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [CHANGELOG.md](CHANGELOG.md) - 变更日志

## 许可证

MIT
