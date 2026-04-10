# 校园百事通 - 使用说明

## 快速启动

### 1. 启动后端服务

```bash
# 进入项目目录
cd campus_helper

# 激活虚拟环境
venv\Scripts\activate

# 启动后端
python backend/main.py
```

看到 `Uvicorn running on http://0.0.0.0:8000` 表示启动成功。

### 2. 打开前端界面

直接用浏览器打开 `frontend/index.html` 文件。

或者访问 http://localhost:8000 查看API文档。

## 功能说明

### 支持的问题类型

1. **政策咨询**
   - "图书馆开放时间"
   - "奖学金怎么申请"
   - "国家奖学金条件"

2. **办事流程**
   - "在读证明怎么办理"
   - "成绩单怎么打印"
   - "选课流程是什么"

3. **校园生活**
   - "宿舍报修"
   - "校园卡使用"
   - "请假流程"

### 快速回复按钮

前端界面提供了常用问题的快捷按钮，点击即可快速提问。

## 配置说明

### YAML 配置文件结构

项目采用 YAML 配置文件分离方案，配置文件位于 `config/` 目录：

```
config/
├── settings.yaml        # 公共配置（可提交到版本控制）
└── settings.local.yaml  # 本地私有配置（包含API密钥，不提交）
```

#### settings.yaml - 公共配置

公共配置文件包含所有非敏感的系统配置：

```yaml
# 应用配置
app:
  name: 校园百事通
  version: 1.1.0
  debug: true
  host: 0.0.0.0
  port: 8000

# 向量数据库配置
vector_db:
  persist_dir: ./data/knowledge_base
  collection_name: campus_knowledge

# LLM配置
llm:
  provider: deepseek    # 当前使用的提供商

  providers:
    deepseek:
      base_url: https://api.deepseek.com/v1
      model: deepseek-chat
      max_tokens: 1000
      temperature: 0.7
    zhipu:
      base_url: https://open.bigmodel.cn/api/paas/v4/
      model: glm-4.7-flash
    openai:
      base_url: https://api.openai.com/v1
      model: gpt-3.5-turbo

# Embedding模型配置
embedding:
  model: BAAI/bge-large-zh-v1.5
  device: cpu
  cache_dir: ./models/embedding

# RAG配置
rag:
  top_k: 5
  similarity_threshold: 0.0
  chunk_size: 400
  chunk_overlap: 50

# 缓存配置
cache:
  enabled: true
  max_size: 1000
  ttl_seconds: 3600
  similarity_threshold: 0.95
```

#### settings.local.yaml - 本地私有配置

用于存放敏感信息（API密钥等），此文件已在 `.gitignore` 中排除：

```yaml
# 本地私有配置 - 此文件不会上传到GitHub
llm:
  provider: deepseek

  providers:
    deepseek:
      api_key: "your-deepseek-api-key"

    zhipu:
      api_key: "your-zhipu-api-key"

    openai:
      api_key: "your-openai-api-key"

# 安全配置
security:
  secret_key: "your-secret-key"
```

### 配置加载机制

配置加载器会按顺序加载并合并配置：

1. 先加载 `settings.yaml` 作为基础配置
2. 再加载 `settings.local.yaml` 覆盖相同配置项
3. 本地配置中的值会覆盖公共配置中的值

这样可以保证敏感信息只存在于本地，不会泄露到版本控制系统。

### 多 LLM 提供商切换指南

系统支持多个 LLM 提供商，可以在配置文件中灵活切换。

#### 支持的提供商

| 提供商 | 标识符 | 默认模型 | 特点 |
|--------|--------|----------|------|
| DeepSeek | `deepseek` | deepseek-chat | 国产大模型，性价比高 |
| 智谱AI | `zhipu` | glm-4.7-flash | 国产大模型，中文能力强 |
| OpenAI | `openai` | gpt-3.5-turbo | 国际大模型，功能全面 |
| Anthropic | `anthropic` | claude-3-sonnet | 国际大模型，安全可靠 |
| 本地模型 | `local` | qwen:7b | 隐私保护，需本地部署 |

#### 切换步骤

**方法一：修改 settings.local.yaml（推荐）**

```yaml
llm:
  provider: zhipu    # 切换到智谱AI

  providers:
    zhipu:
      api_key: "your-zhipu-api-key"    # 填写对应API密钥
```

**方法二：修改 settings.yaml**

直接修改公共配置文件中的 `provider` 字段：

```yaml
llm:
  provider: openai    # 切换到OpenAI
```

#### 各提供商配置示例

**DeepSeek 配置：**

```yaml
llm:
  provider: deepseek
  providers:
    deepseek:
      base_url: https://api.deepseek.com/v1
      model: deepseek-chat
      max_tokens: 1000
      temperature: 0.7
      timeout: 120.0
      api_key: "sk-xxxxx"    # 在 settings.local.yaml 中填写
```

获取API密钥：https://platform.deepseek.com/

**智谱AI 配置：**

```yaml
llm:
  provider: zhipu
  providers:
    zhipu:
      base_url: https://open.bigmodel.cn/api/paas/v4/
      model: glm-4.7-flash
      max_tokens: 1000
      temperature: 0.7
      timeout: 120.0
      api_key: "xxxxx.xxxxx"    # 在 settings.local.yaml 中填写
```

获取API密钥：https://open.bigmodel.cn/

**OpenAI 配置：**

```yaml
llm:
  provider: openai
  providers:
    openai:
      base_url: https://api.openai.com/v1
      model: gpt-3.5-turbo
      max_tokens: 1000
      temperature: 0.7
      api_key: "sk-xxxxx"    # 在 settings.local.yaml 中填写
```

获取API密钥：https://platform.openai.com/

**本地模型 配置：**

```yaml
llm:
  provider: local
  providers:
    local:
      url: http://localhost:11434    # Ollama 服务地址
      model: qwen:7b
```

需要先安装并启动 Ollama：https://ollama.ai/

## API接口

### 对话接口

**POST** `/api/chat`

请求体：
```json
{
    "message": "图书馆开放时间",
    "session_id": "session_123",
    "user_id": "user_456",
    "user_info": {
        "name": "张三",
        "college": "计算机学院"
    }
}
```

响应：
```json
{
    "answer": "图书馆开放时间如下...",
    "type": "knowledge_qa",
    "sources": [{"title": "图书馆开放时间"}],
    "data": null,
    "cached": false
}
```

### 知识库接口

**搜索知识库**

**GET** `/api/knowledge/search?query=图书馆&top_k=5`

响应：
```json
{
    "query": "图书馆",
    "results": [
        {
            "content": "图书馆开放时间为...",
            "metadata": {"title": "图书馆服务指南", "source": "官网"},
            "score": 0.89
        }
    ]
}
```

**添加文档**

**POST** `/api/knowledge/documents`

请求体：
```json
{
    "content": "文档内容",
    "title": "文档标题",
    "source": "来源",
    "doc_type": "policy"
}
```

**知识库统计**

**GET** `/api/knowledge/stats`

响应：
```json
{
    "total_documents": 100,
    "total_chunks": 500,
    "last_updated": "2024-01-01T00:00:00"
}
```

### 缓存管理接口

系统内置智能答案缓存，支持精确匹配和语义相似度匹配，可大幅提升响应速度。

**查看缓存统计**

**GET** `/api/cache/stats`

响应：
```json
{
    "enabled": true,
    "total_requests": 1250,
    "cache_hits": 875,
    "cache_misses": 375,
    "evictions": 12,
    "hit_rate": 0.70,
    "current_size": 156,
    "max_size": 1000,
    "ttl_seconds": 3600,
    "similarity_threshold": 0.95
}
```

字段说明：
- `total_requests`: 总请求数
- `cache_hits`: 缓存命中次数
- `cache_misses`: 缓存未命中次数
- `evictions`: 被淘汰的缓存条目数
- `hit_rate`: 缓存命中率（0-1）
- `current_size`: 当前缓存条目数
- `max_size`: 最大缓存容量
- `ttl_seconds`: 缓存过期时间（秒）
- `similarity_threshold`: 语义相似度匹配阈值

**清空缓存**

**POST** `/api/cache/clear`

响应：
```json
{
    "success": true,
    "cleared_count": 156,
    "message": "已清空 156 条缓存"
}
```

**查看缓存条目**

**GET** `/api/cache/entries?limit=100`

响应：
```json
{
    "count": 50,
    "entries": [
        {
            "key": "a1b2c3d4e5f6...",
            "query": "图书馆开放时间",
            "intent": "knowledge_qa",
            "hit_count": 5,
            "created_at": "2024-01-01T10:00:00",
            "expires_at": "2024-01-01T11:00:00",
            "is_expired": false
        }
    ]
}
```

### 系统接口

**健康检查**

**GET** `/api/system/health`

响应：
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00"
}
```

**获取系统配置**

**GET** `/api/system/config`

响应：
```json
{
    "app_name": "校园百事通",
    "version": "1.0.0",
    "llm_provider": "deepseek",
    "embedding_model": "BAAI/bge-large-zh-v1.5"
}
```

### 用户接口

**绑定用户身份**

**POST** `/api/user/bind`

请求体：
```json
{
    "user_id": "user_123",
    "student_id": "20210001",
    "name": "张三"
}
```

**获取用户信息**

**GET** `/api/user/info/{user_id}`

## 添加知识

### 方式一：运行示例数据脚本

```bash
python scripts/load_sample_data.py
```

### 方式二：通过API添加

```bash
curl -X POST http://localhost:8000/api/knowledge/documents \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"文档内容\",\"title\":\"标题\",\"source\":\"来源\",\"doc_type\":\"policy\"}"
```

## 常见问题

### Q: 后端启动报错？

检查是否安装了所有依赖：
```bash
pip install -r requirements.txt
```

### Q: 前端无法连接后端？

1. 确认后端已启动
2. 检查端口8000是否被占用
3. 查看浏览器控制台错误信息

### Q: 回答不准确？

1. 检查知识库是否有相关内容
2. 尝试换种方式提问
3. 添加更多相关知识到知识库

### Q: 如何切换LLM提供商？

修改 `config/settings.local.yaml` 中的 `llm.provider` 字段，并填写对应的API密钥。

### Q: 缓存命中率低怎么办？

1. 检查用户提问的相似度，相似问题会通过语义匹配命中缓存
2. 可以在 `settings.yaml` 中调整 `cache.similarity_threshold` 降低匹配阈值
3. 确保 `cache.enabled` 为 `true`

## 项目结构

```
campus_helper/
├── backend/              # 后端代码
│   ├── api/             # API路由
│   │   └── routes.py    # 路由定义（含缓存API）
│   ├── services/        # 核心服务
│   │   ├── answer_cache.py    # 缓存服务
│   │   ├── rag_retriever.py   # RAG检索
│   │   └── agent_workflow.py  # Agent工作流
│   ├── models/          # 数据模型
│   │   ├── schemas.py   # API模型
│   │   └── cache_models.py    # 缓存模型
│   └── main.py          # 启动入口
├── frontend/            # 前端界面
│   └── index.html
├── config/              # 配置文件
│   ├── settings.yaml        # 公共配置
│   ├── settings.local.yaml  # 本地私有配置
│   └── loader.py            # 配置加载器
├── scripts/             # 工具脚本
├── data/                # 数据文件
├── models/              # 模型文件
│   └── embedding/       # Embedding模型
└── tests/               # 测试代码
```

## 技术支持

- API文档: http://localhost:8000/docs
- 项目进度: PROJECT_PROGRESS.md
