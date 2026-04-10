# 校园百事通配置指南

本文档详细介绍校园百事通项目的配置系统，帮助您正确配置和部署应用。

---

## 目录

1. [配置文件结构](#配置文件结构)
2. [settings.yaml 公共配置详解](#settingsyaml-公共配置详解)
3. [settings.local.yaml 私有配置详解](#settingslocalyaml-私有配置详解)
4. [各LLM提供商配置示例](#各llm提供商配置示例)
5. [Embedding模型配置说明](#embedding模型配置说明)
6. [RAG参数调优指南](#rag参数调优指南)
7. [缓存配置说明](#缓存配置说明)
8. [安全配置说明](#安全配置说明)
9. [配置最佳实践](#配置最佳实践)

---

## 配置文件结构

### 文件位置

```
campus_helper/
├── config/
│   ├── settings.yaml          # 公共配置（可提交到Git）
│   ├── settings.local.yaml    # 私有配置（包含敏感信息，不提交）
│   ├── __init__.py
│   └── loader.py              # 配置加载器
```

### 配置加载机制

项目采用 **分层配置** 策略，加载顺序如下：

1. **settings.yaml** - 公共配置，存储在版本控制中
2. **settings.local.yaml** - 本地私有配置，会覆盖公共配置中的相同项

配置加载器使用深度合并（Deep Merge）算法，`settings.local.yaml` 中的配置会递归覆盖 `settings.yaml` 中的对应值。

```python
# 配置加载示例
# settings.yaml
llm:
  provider: deepseek
  providers:
    deepseek:
      api_key: ""

# settings.local.yaml
llm:
  providers:
    deepseek:
      api_key: "your-real-api-key"

# 最终合并结果
llm:
  provider: deepseek
  providers:
    deepseek:
      api_key: "your-real-api-key"
```

### 配置验证

配置加载后会自动转换为 Python dataclass 对象，提供类型提示和默认值：

```python
from config import settings, get_settings

# 方式一：使用全局单例
print(settings.app.name)        # "校园百事通"
print(settings.llm.provider)    # "deepseek"

# 方式二：获取配置对象
config = get_settings()
print(config.rag.top_k)         # 5
```

---

## settings.yaml 公共配置详解

### app 应用配置

```yaml
app:
  name: 校园百事通      # 应用名称
  version: 1.0.0       # 应用版本
  debug: true          # 调试模式（生产环境设为 false）
  host: 0.0.0.0        # 服务监听地址
  port: 8000           # 服务端口
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | "校园百事通" | 应用显示名称 |
| `version` | string | "1.0.0" | 应用版本号 |
| `debug` | bool | true | 开启调试模式，输出详细日志 |
| `host` | string | "0.0.0.0" | 服务绑定地址，本地开发可设为 `127.0.0.1` |
| `port` | int | 8000 | 服务端口号 |

**注意事项**：
- 生产环境务必将 `debug` 设为 `false`
- `host: 0.0.0.0` 允许外部访问，本地开发可改为 `127.0.0.1`

---

### database 数据库配置

```yaml
database:
  url: sqlite:///./data/campus_helper.db
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | "sqlite:///./data/campus_helper.db" | 数据库连接字符串 |

**支持的数据库类型**：

```yaml
# SQLite（默认）
database:
  url: sqlite:///./data/campus_helper.db

# MySQL
database:
  url: mysql+pymysql://user:password@localhost:3306/campus_helper

# PostgreSQL
database:
  url: postgresql://user:password@localhost:5432/campus_helper
```

---

### vector_db 向量数据库配置

```yaml
vector_db:
  persist_dir: ./data/knowledge_base    # 向量数据库持久化目录
  collection_name: campus_knowledge     # 集合名称
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `persist_dir` | string | "./data/knowledge_base" | Chroma 向量数据库存储路径 |
| `collection_name` | string | "campus_knowledge" | 向量集合名称，区分不同知识库 |

**使用建议**：
- 不同环境可使用不同的 `collection_name`（如 `dev_knowledge`, `prod_knowledge`）
- 确保 `persist_dir` 目录有写入权限

---

### llm 大模型配置

```yaml
llm:
  provider: deepseek                   # 当前使用的提供商

  providers:
    deepseek:                          # DeepSeek 配置
      base_url: https://api.deepseek.com/v1
      model: deepseek-chat
      max_tokens: 1000
      temperature: 0.7
      timeout: 120.0
      api_key: ""

    zhipu:                             # 智谱AI 配置
      base_url: https://open.bigmodel.cn/api/paas/v4/
      model: glm-4.7-flash
      max_tokens: 1000
      temperature: 0.7
      timeout: 120.0
      api_key: ""

    openai:                            # OpenAI 配置
      base_url: https://api.openai.com/v1
      model: gpt-3.5-turbo
      max_tokens: 1000
      temperature: 0.7
      api_key: ""

    anthropic:                         # Anthropic 配置
      model: claude-3-sonnet-20240229
      max_tokens: 1000
      api_key: ""

    local:                             # 本地模型（Ollama）
      url: http://localhost:11434
      model: qwen:7b
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | string | "deepseek" | 当前激活的 LLM 提供商 |
| `providers.<name>.api_key` | string | "" | API 密钥（在 settings.local.yaml 中配置） |
| `providers.<name>.base_url` | string | - | API 基础 URL |
| `providers.<name>.model` | string | - | 模型名称 |
| `providers.<name>.max_tokens` | int | 1000 | 最大生成 token 数 |
| `providers.<name>.temperature` | float | 0.7 | 生成温度（0-1） |
| `providers.<name>.timeout` | float | 120.0 | 请求超时时间（秒） |

**provider 可选值**：
- `deepseek` - DeepSeek（推荐，性价比高）
- `zhipu` - 智谱AI（国内访问稳定）
- `openai` - OpenAI
- `anthropic` - Anthropic Claude
- `local` - Ollama 本地模型

---

### embedding 嵌入模型配置

```yaml
embedding:
  model: BAAI/bge-large-zh-v1.5    # 模型名称
  device: cpu                      # 运行设备
  cache_dir: ./models/embedding    # 模型缓存目录
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | string | "BAAI/bge-large-zh-v1.5" | HuggingFace 模型名称 |
| `device` | string | "cpu" | 运行设备：`cpu` 或 `cuda` |
| `cache_dir` | string | "./models/embedding" | 模型下载缓存目录 |

**推荐模型**：

| 模型 | 语言 | 维度 | 说明 |
|------|------|------|------|
| `BAAI/bge-large-zh-v1.5` | 中文 | 1024 | 推荐，中文效果好 |
| `BAAI/bge-base-zh-v1.5` | 中文 | 768 | 轻量版 |
| `BAAI/bge-m3` | 多语言 | 1024 | 支持中英混合 |
| `text-embedding-ada-002` | 多语言 | 1536 | OpenAI API |

---

### rag 检索配置

```yaml
rag:
  top_k: 5                    # 检索返回数量
  similarity_threshold: 0.0   # 相似度阈值
  chunk_size: 400             # 文本块大小
  chunk_overlap: 50           # 文本块重叠
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `top_k` | int | 5 | 检索返回的相关文档数量 |
| `similarity_threshold` | float | 0.0 | 相似度过滤阈值（0-1），0 表示不过滤 |
| `chunk_size` | int | 400 | 文本分块大小（字符数） |
| `chunk_overlap` | int | 50 | 相邻文本块重叠字符数 |

**参数调优建议**：

| 场景 | top_k | similarity_threshold | chunk_size | chunk_overlap |
|------|-------|---------------------|------------|---------------|
| 快速响应 | 3 | 0.3 | 300 | 30 |
| 平衡模式 | 5 | 0.0 | 400 | 50 |
| 深度检索 | 10 | 0.0 | 500 | 100 |
| 长文本知识 | 5 | 0.0 | 800 | 100 |

---

### bm25 配置

```yaml
bm25:
  k1: 1.5      # 词频饱和参数
  b: 0.75      # 文档长度归一化参数
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `k1` | float | 1.5 | 控制词频对评分的影响（1.2-2.0） |
| `b` | float | 0.75 | 控制文档长度归一化程度（0-1） |

**参数说明**：
- `k1` 值越大，词频对评分的影响越大
- `b` 值越大，长文档的惩罚越重
- 默认值适用于大多数场景，通常无需调整

---

### cache 缓存配置

```yaml
cache:
  enabled: true                 # 是否启用缓存
  max_size: 1000                # 最大缓存条目数
  ttl_seconds: 3600             # 缓存过期时间（秒）
  similarity_threshold: 0.95    # 语义缓存相似度阈值
  stats_enabled: true           # 是否启用统计
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | true | 是否启用语义缓存 |
| `max_size` | int | 1000 | 最大缓存条目数 |
| `ttl_seconds` | int | 3600 | 缓存有效期（秒） |
| `similarity_threshold` | float | 0.95 | 语义匹配阈值，越高越严格 |
| `stats_enabled` | bool | true | 是否记录缓存命中率统计 |

**缓存工作原理**：
1. 新问题与缓存中的问题进行语义相似度计算
2. 相似度超过阈值时，直接返回缓存的答案
3. 缓存过期或满时自动清理旧条目

---

### security 安全配置

```yaml
security:
  secret_key: ""                    # 应用密钥（必填）
  token_expire_minutes: 60          # Token 过期时间（分钟）
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `secret_key` | string | "" | 应用密钥，用于加密签名 |
| `token_expire_minutes` | int | 60 | 用户登录 Token 有效期 |

**重要**：`secret_key` 必须在 `settings.local.yaml` 中设置，不要提交到版本控制。

---

### logging 日志配置

```yaml
logging:
  level: INFO                              # 日志级别
  file: ./logs/campus_helper.log           # 日志文件路径
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | string | "INFO" | 日志级别：DEBUG, INFO, WARNING, ERROR |
| `file` | string | "./logs/campus_helper.log" | 日志文件路径 |

---

## settings.local.yaml 私有配置详解

### 文件用途

`settings.local.yaml` 用于存储敏感信息和本地特定配置：

- API 密钥
- 数据库密码
- 应用密钥
- 本地开发特定配置

### 配置示例

```yaml
# settings.local.yaml - 本地私有配置
# 此文件不会上传到 GitHub

# LLM 配置
llm:
  provider: deepseek           # 可覆盖默认提供商

  providers:
    deepseek:
      api_key: "sk-your-deepseek-api-key"

    zhipu:
      api_key: "your-zhipu-api-key"

    openai:
      api_key: "sk-your-openai-api-key"

    anthropic:
      api_key: "sk-ant-your-anthropic-api-key"

# 安全配置
security:
  secret_key: "your-random-secret-key-at-least-32-chars"
```

### .gitignore 配置

确保私有配置不被提交：

```gitignore
# 配置文件
config/settings.local.yaml
```

---

## 各LLM提供商配置示例

### DeepSeek 配置（推荐）

DeepSeek 是性价比最高的选择，国内访问稳定。

```yaml
llm:
  provider: deepseek
  providers:
    deepseek:
      base_url: https://api.deepseek.com/v1
      model: deepseek-chat           # 或 deepseek-coder
      max_tokens: 2000
      temperature: 0.7
      timeout: 120.0
      api_key: "sk-xxxxxxxxxxxxxxxx"
```

**可用模型**：
- `deepseek-chat` - 通用对话模型
- `deepseek-coder` - 代码专用模型

**获取 API Key**：https://platform.deepseek.com/

---

### 智谱AI 配置

智谱AI 是国内大模型厂商，访问稳定，支持中文。

```yaml
llm:
  provider: zhipu
  providers:
    zhipu:
      base_url: https://open.bigmodel.cn/api/paas/v4/
      model: glm-4.7-flash           # 或 glm-4, glm-4-plus
      max_tokens: 2000
      temperature: 0.7
      timeout: 120.0
      api_key: "xxxxxxxx.xxxxxxxxxxxxxxxx"
```

**可用模型**：
- `glm-4.7-flash` - 免费模型，速度快（推荐）
- `glm-4-flash` - 快速响应
- `glm-4` - 标准模型
- `glm-4-plus` - 增强模型

**获取 API Key**：https://open.bigmodel.cn/

---

### OpenAI 配置

需要科学上网访问。

```yaml
llm:
  provider: openai
  providers:
    openai:
      base_url: https://api.openai.com/v1
      model: gpt-3.5-turbo           # 或 gpt-4, gpt-4-turbo
      max_tokens: 2000
      temperature: 0.7
      api_key: "sk-xxxxxxxxxxxxxxxx"
```

**可用模型**：
- `gpt-3.5-turbo` - 性价比高
- `gpt-4` - 效果最好
- `gpt-4-turbo` - GPT-4 增强版

**获取 API Key**：https://platform.openai.com/

---

### Anthropic 配置

Claude 系列模型，需要科学上网。

```yaml
llm:
  provider: anthropic
  providers:
    anthropic:
      model: claude-3-sonnet-20240229
      max_tokens: 2000
      api_key: "sk-ant-xxxxxxxxxxxxxxxx"
```

**可用模型**：
- `claude-3-opus-20240229` - 最强
- `claude-3-sonnet-20240229` - 平衡
- `claude-3-haiku-20240307` - 快速

**获取 API Key**：https://console.anthropic.com/

---

### Ollama 本地配置

完全本地运行，无需 API 费用，但需要较好的硬件。

```yaml
llm:
  provider: local
  providers:
    local:
      url: http://localhost:11434
      model: qwen:7b                 # 或 llama2, mistral 等
```

**前置条件**：
1. 安装 Ollama：https://ollama.ai/
2. 下载模型：`ollama pull qwen:7b`
3. 启动服务：`ollama serve`

**推荐模型**：
- `qwen:7b` - 通义千问，中文效果好
- `qwen:14b` - 更大版本，效果更好
- `llama2:7b` - Meta LLaMA 2
- `mistral:7b` - Mistral 模型

---

## Embedding模型配置说明

### 模型选择

| 模型 | 语言 | 大小 | 推荐场景 |
|------|------|------|----------|
| `BAAI/bge-large-zh-v1.5` | 中文 | 1.3GB | 中文知识库（推荐） |
| `BAAI/bge-base-zh-v1.5` | 中文 | 400MB | 资源受限环境 |
| `BAAI/bge-m3` | 多语言 | 2.2GB | 中英混合知识库 |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 多语言 | 470MB | 轻量多语言 |

### 设备配置

```yaml
embedding:
  model: BAAI/bge-large-zh-v1.5
  device: cpu      # 使用 CPU
  # device: cuda   # 使用 GPU（需要 CUDA）
```

**GPU 加速**：
- 安装 CUDA 版本的 PyTorch
- 设置 `device: cuda`
- 首次加载会慢，后续会使用缓存

### 模型缓存

首次运行时会自动下载模型到 `cache_dir` 指定的目录：

```yaml
embedding:
  cache_dir: ./models/embedding
```

---

## RAG参数调优指南

### 检索质量优化

#### top_k 参数

```yaml
rag:
  top_k: 5    # 返回 5 个最相关的文档块
```

**调优建议**：
- **小知识库**（<100条）：`top_k: 3-5`
- **中型知识库**（100-1000条）：`top_k: 5-10`
- **大型知识库**（>1000条）：`top_k: 10-20`

#### similarity_threshold 参数

```yaml
rag:
  similarity_threshold: 0.0    # 不过滤
  # similarity_threshold: 0.3  # 过滤低相关性结果
```

**调优建议**：
- **高准确率需求**：设置 `0.3-0.5`
- **高召回率需求**：设置 `0.0`
- **平衡模式**：设置 `0.1-0.2`

### 分块策略优化

#### chunk_size 参数

```yaml
rag:
  chunk_size: 400    # 每个文档块 400 字符
```

**调优建议**：
- **问答场景**：`200-400` 字符
- **长文档理解**：`600-1000` 字符
- **代码文档**：`500-800` 字符

#### chunk_overlap 参数

```yaml
rag:
  chunk_overlap: 50   # 相邻块重叠 50 字符
```

**调优建议**：
- 一般设置为 `chunk_size` 的 10%-15%
- 长文本知识库可增加到 `chunk_size` 的 20%

### 配置示例

#### 快速响应配置

```yaml
rag:
  top_k: 3
  similarity_threshold: 0.3
  chunk_size: 300
  chunk_overlap: 30
```

#### 深度检索配置

```yaml
rag:
  top_k: 10
  similarity_threshold: 0.0
  chunk_size: 600
  chunk_overlap: 100
```

---

## 缓存配置说明

### 语义缓存原理

校园百事通使用语义缓存，当新问题与缓存中的问题语义相似度超过阈值时，直接返回缓存的答案，避免重复调用 LLM API。

### 配置参数

```yaml
cache:
  enabled: true                 # 启用缓存
  max_size: 1000                # 最多缓存 1000 条
  ttl_seconds: 3600             # 缓存 1 小时后过期
  similarity_threshold: 0.95    # 相似度阈值 95%
  stats_enabled: true           # 记录统计信息
```

### 调优建议

| 场景 | enabled | max_size | ttl_seconds | similarity_threshold |
|------|---------|----------|-------------|---------------------|
| 高频重复问题 | true | 2000 | 7200 | 0.95 |
| 一般场景 | true | 1000 | 3600 | 0.95 |
| 实时性要求高 | true | 500 | 1800 | 0.98 |
| 开发调试 | false | - | - | - |

### 缓存命中率统计

启用 `stats_enabled: true` 后，可通过 API 查看缓存统计：

```python
# 获取缓存统计
from backend.services.cache_service import cache_service

stats = cache_service.get_stats()
print(f"命中率: {stats['hit_rate']:.2%}")
```

---

## 安全配置说明

### secret_key 配置

`secret_key` 用于 JWT Token 签名和加密，必须设置为随机字符串。

**生成安全密钥**：

```python
import secrets
print(secrets.token_urlsafe(32))
```

**配置**：

```yaml
# settings.local.yaml
security:
  secret_key: "生成的随机字符串"
  token_expire_minutes: 60
```

### 生产环境检查清单

- [ ] `secret_key` 已设置为随机字符串（至少 32 字符）
- [ ] `app.debug` 设为 `false`
- [ ] API 密钥存储在 `settings.local.yaml` 中
- [ ] `settings.local.yaml` 已加入 `.gitignore`
- [ ] 数据库使用强密码（如使用 MySQL/PostgreSQL）
- [ ] 使用 HTTPS（如部署到服务器）

---

## 配置最佳实践

### 1. 分离敏感信息

**正确做法**：

```yaml
# settings.yaml（提交到 Git）
llm:
  provider: deepseek
  providers:
    deepseek:
      model: deepseek-chat
      api_key: ""    # 留空

# settings.local.yaml（不提交）
llm:
  providers:
    deepseek:
      api_key: "sk-real-api-key"
```

**错误做法**：

```yaml
# settings.yaml（提交到 Git）
llm:
  providers:
    deepseek:
      api_key: "sk-real-api-key"    # 危险！密钥会泄露
```

### 2. 环境区分

开发环境和生产环境使用不同的配置：

```yaml
# 开发环境 settings.local.yaml
app:
  debug: true

llm:
  provider: zhipu    # 使用便宜的测试模型

# 生产环境 settings.local.yaml
app:
  debug: false

llm:
  provider: deepseek    # 使用正式模型
```

### 3. 配置验证

启动时验证必要配置：

```python
from config import settings

def validate_config():
    # 检查必要配置
    if not settings.llm.get_current_provider().api_key:
        raise ValueError("请配置 LLM API Key")

    if not settings.security.secret_key:
        raise ValueError("请配置 secret_key")

    # 检查目录
    import os
    os.makedirs(settings.vector_db.persist_dir, exist_ok=True)
```

### 4. 配置文档同步

修改配置时同步更新本文档，确保文档与实际配置一致。

### 5. 备份配置

定期备份 `settings.local.yaml` 到安全位置（如密码管理器）。

---

## 快速配置模板

### 最小配置（settings.local.yaml）

```yaml
# 最小配置 - 只需填写 API Key
llm:
  provider: deepseek
  providers:
    deepseek:
      api_key: "sk-your-api-key"

security:
  secret_key: "your-random-secret-key-32-chars"
```

### 完整配置模板

```yaml
# 完整配置示例
app:
  debug: false

llm:
  provider: deepseek
  providers:
    deepseek:
      api_key: "sk-your-deepseek-key"
    zhipu:
      api_key: "your-zhipu-key"

embedding:
  device: cuda

rag:
  top_k: 8
  chunk_size: 500

cache:
  max_size: 2000
  ttl_seconds: 7200

security:
  secret_key: "your-32-char-secret-key-here"
  token_expire_minutes: 120

logging:
  level: INFO
```

---

## 常见问题

### Q: 如何切换 LLM 提供商？

修改 `settings.local.yaml` 中的 `llm.provider` 值：

```yaml
llm:
  provider: zhipu    # 切换到智谱 AI
```

### Q: API Key 配置了但不生效？

检查配置格式是否正确，确保 YAML 缩进正确：

```yaml
# 正确
llm:
  providers:
    deepseek:
      api_key: "sk-xxx"

# 错误（缩进不对）
llm:
 providers:
   deepseek:
   api_key: "sk-xxx"
```

### Q: 如何查看当前配置？

```python
from config import settings

print(f"LLM 提供商: {settings.llm.provider}")
print(f"当前模型: {settings.llm.get_current_provider().model}")
print(f"RAG top_k: {settings.rag.top_k}")
```

### Q: 配置修改后需要重启吗？

是的，修改配置后需要重启应用才能生效。

---

## 相关文档

- [README.md](README.md) - 项目介绍
- [USAGE.md](USAGE.md) - 使用说明
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构文档

---

*最后更新：2026年4月*
