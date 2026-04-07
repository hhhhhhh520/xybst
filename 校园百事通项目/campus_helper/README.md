# 校园百事通智能服务系统

基于RAG与Agent技术的校园智能问答系统，使用Python + FastAPI + Vue.js实现。

## 技术栈

- **后端**: Python 3.9+, FastAPI, LangChain, ChromaDB
- **前端**: Vue.js 3, Element Plus
- **AI模型**: 支持OpenAI/Claude/本地模型
- **向量数据库**: ChromaDB
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

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写API密钥等配置
```

### 3. 准备知识库

```bash
# 将校园文档放入 data/raw_docs/
# 支持格式: PDF, Word, TXT, Markdown

# 处理文档
python scripts/process_documents.py
```

### 4. 启动服务

```bash
# 启动后端
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
├── backend/              # 后端代码
│   ├── api/             # API路由
│   ├── core/            # 核心模块
│   ├── models/          # 数据模型
│   ├── services/        # 业务逻辑
│   └── main.py          # 入口文件
├── frontend/            # 前端代码
│   ├── src/
│   └── package.json
├── data/                # 数据文件
│   ├── raw_docs/        # 原始文档
│   ├── processed/       # 处理后文档
│   └── knowledge_base/  # 向量数据库
├── config/              # 配置文件
├── scripts/             # 工具脚本
└── tests/               # 测试代码
```

## 核心功能

- 🤖 智能问答：基于RAG的校园政策咨询
- 📚 知识库管理：文档上传、分块、索引
- 💬 多轮对话：上下文理解和记忆
- 🔍 混合检索：向量+关键词检索
- 📊 效果评估：回答质量评估和优化

## 许可证

MIT
