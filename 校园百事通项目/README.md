# 校园百事通智能体项目

> 基于 RAG 与 Agent 技术的校园智能服务系统

## 项目简介

校园百事通是一个面向高校师生的 AI 智能服务系统，采用 Python 本地部署方案，基于 RAG（检索增强生成）和 Agent 技术，提供 7×24 小时的校园信息咨询服务。

**核心功能**：
- 🤖 智能问答：基于知识库回答校园政策咨询
- 📅 个性化查询：课表、成绩等个人信息查询
- 📋 事务向导：办事流程指引、材料清单
- 💬 多轮对话：支持上下文理解

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| LLM 框架 | LangChain |
| 向量数据库 | ChromaDB |
| Embedding | BAAI/bge-large-zh-v1.5 |
| 分词 | Jieba |
| 文档处理 | PyPDF, python-docx, unstructured |

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户交互层                          │
│                    Web 前端界面                          │
└─────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    FastAPI 服务层                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Agent核心   │  │   RAG模块    │  │   API路由    │  │
│  │  - 意图识别   │  │  - 向量检索  │  │  - 对话接口  │  │
│  │  - 对话管理   │  │  - BM25检索  │  │  - 健康检查  │  │
│  │  - 任务规划   │  │  - 答案生成  │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                         数据层                           │
│     ChromaDB向量库    知识文档    日志数据               │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
校园百事通项目/
├── campus_helper/              # 主项目代码
│   ├── backend/                # 后端服务
│   │   ├── api/                # API 路由
│   │   ├── core/               # 核心配置
│   │   ├── models/             # 数据模型
│   │   ├── services/           # 业务服务
│   │   │   ├── rag_retriever.py      # RAG 检索
│   │   │   ├── knowledge_base.py     # 知识库管理
│   │   │   ├── agent_workflow.py     # Agent 工作流
│   │   │   ├── llm_service.py        # LLM 服务
│   │   │   └── bm25.py               # BM25 检索
│   │   └── main.py             # 入口文件
│   ├── frontend/               # 前端界面
│   ├── models/                 # 本地模型
│   │   └── embedding/BAAI_bge-large-zh-v1.5/
│   ├── data/                   # 知识文档
│   ├── config/                 # 配置文件
│   ├── scripts/                # 工具脚本
│   ├── tests/                  # 测试用例
│   ├── requirements.txt        # 依赖清单
│   └── .env                    # 环境变量
├── 01-需求分析/                # 需求调研文档
├── 02-知识库文档/              # 知识库搭建方案
├── 03-Prompt设计/              # 提示词设计
├── 04-工作流配置/              # Agent 工作流设计
├── 05-测试用例/                # 测试与优化
├── 06-项目成果/                # 成果与数据
├── 07-论文素材/                # 毕设与面试材料
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/你的用户名/xybst.git
cd xybst/校园百事通项目/campus_helper

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

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，配置以下内容：
# - OPENAI_API_KEY 或 ANTHROPIC_API_KEY
# - 其他自定义配置
```

### 3. 下载 Embedding 模型

首次运行会自动下载 BAAI/bge-large-zh-v1.5 模型，或手动放置到：
```
models/embedding/BAAI_bge-large-zh-v1.5/
```

### 4. 准备知识库

将校园文档（PDF、Word、TXT 等）放入 `data/` 目录，然后运行：

```bash
python scripts/process_documents.py
```

### 5. 启动服务

```bash
# 启动后端服务
python backend/main.py

# 或使用启动脚本（Windows）
start.bat
```

服务启动后访问：
- 前端界面：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 核心配置

### 知识库配置

```yaml
embedding_model: BAAI/bge-large-zh-v1.5
chunk_size: 400
chunk_overlap: 50
top_k: 10
similarity_threshold: 0.75
```

### 检索配置

```yaml
retrieval:
  vector_weight: 0.7
  bm25_weight: 0.3
  rerank: true
  rerank_top_n: 5
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 对话接口 |
| `/api/chat/stream` | POST | 流式对话 |
| `/health` | GET | 健康检查 |

### 对话示例

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "图书馆几点开门？", "session_id": "test"}'
```

## 技术亮点

- **混合检索策略**：向量检索 + BM25 关键词检索，提升召回准确率
- **本地 Embedding**：使用 bge-large-zh-v1.5 模型，无需外部 API 调用
- **语义分块优化**：针对不同文档类型采用差异化分块策略
- **Agent 工作流**：支持意图识别、多轮对话、任务规划

## 项目成果

| 指标 | 数值 |
|------|------|
| 服务用户 | **856人** |
| 月活跃用户 | **642人** |
| 累计对话 | **18,520轮** |
| 问题解决率 | **82%** |
| 回答准确率 | **88.5%** |
| 用户满意度 | **86%** |

## 项目文档

| 文档 | 说明 |
|------|------|
| [需求分析](01-需求分析/) | 用户调研方案、调研报告、高频问题清单 |
| [知识库文档](02-知识库文档/) | 知识库搭建方案、文档采集清单 |
| [Prompt设计](03-Prompt设计/) | 角色设定、系统提示词、Few-shot 示例 |
| [工作流配置](04-工作流配置/) | Agent 工作流设计 |
| [测试用例](05-测试用例/) | 功能测试用例、效果优化方案 |
| [项目成果](06-项目成果/) | 量化指标、用户反馈、简历描述 |
| [论文素材](07-论文素材/) | 论文框架、面试话术 |

## 开发计划

- [ ] 语音交互功能
- [ ] 微信小程序端
- [ ] 管理后台
- [ ] 数据分析看板

## 许可证

MIT License

## 致谢

感谢学校教务处、学工处等部门提供的政策支持文档
感谢参与用户调研和测试的师生

---

**项目状态**：持续优化中

**最后更新**：2025年4月
