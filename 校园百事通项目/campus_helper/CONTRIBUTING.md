# 贡献指南

感谢你考虑为校园百事通项目做出贡献！本文档将帮助你了解如何参与项目开发。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [分支管理](#分支管理)
- [Pull Request 流程](#pull-request-流程)
- [知识库贡献指南](#知识库贡献指南)
- [问题反馈](#问题反馈)

---

## 行为准则

本项目采用贡献者公约作为行为准则。参与本项目即表示你同意遵守其条款，请保持尊重和包容的交流态度。

---

## 如何贡献

### 贡献类型

我们欢迎以下类型的贡献：

| 类型 | 描述 |
|------|------|
| Bug 修复 | 修复现有功能的问题 |
| 新功能 | 添加新的功能特性 |
| 文档改进 | 完善 README、注释、API 文档等 |
| 知识库内容 | 添加或更新校园知识库文档 |
| 性能优化 | 提升系统性能或响应速度 |
| 测试用例 | 增加测试覆盖率 |
| 翻译 | 多语言支持 |

### 贡献步骤

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的修改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 开发环境搭建

### 系统要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.9+ | 后端运行环境 |
| Node.js | 16+ | 前端开发环境 |
| Git | 2.0+ | 版本控制 |

### 后端环境搭建

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/campus_helper.git
cd campus_helper

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 安装开发工具依赖
pip install black isort flake8 mypy pytest

# 6. 配置本地环境
cp config/settings.yaml config/settings.local.yaml
# 编辑 settings.local.yaml，填写你的 API 密钥

# 7. 启动后端服务
python backend/main.py
```

### 前端环境搭建

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

### 验证环境

```bash
# 运行测试
pytest tests/

# 检查代码风格
flake8 backend/
black --check backend/
isort --check-only backend/

# 类型检查
mypy backend/
```

### 推荐的 IDE 配置

**VS Code 推荐扩展：**

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "charliermarsh.ruff",
    "vue.volar"
  ]
}
```

**VS Code settings.json：**

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "isort.args": ["--profile", "black"]
}
```

---

## 代码规范

### Python 代码规范

本项目遵循 PEP 8 规范，使用以下工具保证代码质量：

#### 格式化工具

| 工具 | 用途 | 配置 |
|------|------|------|
| Black | 代码格式化 | 行宽 88 字符 |
| isort | import 排序 | profile: black |

#### 代码风格要求

```python
# 好的示例：清晰的函数命名和文档字符串
def retrieve_knowledge(
    query: str,
    top_k: int = 5,
    threshold: float = 0.0
) -> List[Document]:
    """
    从知识库检索相关文档。

    Args:
        query: 查询文本
        top_k: 返回的最大文档数量
        threshold: 相似度阈值

    Returns:
        相关文档列表，按相似度降序排列
    """
    pass


# 避免的写法：缺少类型注解和文档
def retrieve(q, k=5, t=0):
    pass
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块名 | 小写+下划线 | `knowledge_base.py` |
| 类名 | 大驼峰 | `KnowledgeBaseService` |
| 函数名 | 小写+下划线 | `get_documents()` |
| 常量 | 大写+下划线 | `MAX_CACHE_SIZE` |
| 私有属性 | 单下划线前缀 | `_internal_cache` |

#### 类型注解

所有公开函数必须有类型注解：

```python
from typing import List, Optional, Dict, Any

def process_documents(
    documents: List[str],
    chunk_size: int = 400,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """处理文档并返回分块结果。"""
    pass
```

#### 日志规范

使用项目统一的 logger：

```python
from core.logger import logger

# 正确用法
logger.info("知识库初始化完成")
logger.warning("API 响应超时，正在重试")
logger.error(f"文档处理失败: {error}", exc_info=True)

# 避免直接使用 print
# print("这条消息不会被记录到日志文件")
```

### 前端代码规范

#### Vue 组件结构

```vue
<template>
  <!-- 模板内容 -->
</template>

<script setup>
// 脚本内容
</script>

<style scoped>
/* 样式内容 */
</style>
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件名 | 大驼峰 | `ChatMessage.vue` |
| props | 小驼峰 | `sendMessage` |
| 事件名 | 小写+连字符 | `@message-sent` |

### 配置文件规范

YAML 配置文件必须包含注释说明：

```yaml
# LLM 配置
llm:
  # 当前使用的提供商
  provider: deepseek

  # 各提供商配置
  providers:
    deepseek:
      # API 基础地址
      base_url: https://api.deepseek.com/v1
      # 模型名称
      model: deepseek-chat
```

---

## 提交规范

本项目采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型（type）

| 类型 | 描述 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加语音输入功能` |
| `fix` | Bug 修复 | `fix: 修复缓存未正确失效的问题` |
| `docs` | 文档更新 | `docs: 更新 API 文档` |
| `style` | 代码格式（不影响功能） | `style: 格式化代码` |
| `refactor` | 重构代码 | `refactor: 重构检索服务` |
| `perf` | 性能优化 | `perf: 优化向量检索速度` |
| `test` | 测试相关 | `test: 添加 RAG 检索单元测试` |
| `chore` | 构建/工具相关 | `chore: 更新依赖版本` |
| `ci` | CI 配置 | `ci: 添加 GitHub Actions 工作流` |
| `kb` | 知识库内容 | `kb: 添加奖学金申请流程文档` |

### 范围（scope）

可选的范围标识，表示影响的模块：

| 范围 | 描述 |
|------|------|
| `api` | API 接口 |
| `rag` | RAG 检索服务 |
| `llm` | LLM 服务 |
| `kb` | 知识库管理 |
| `cache` | 缓存服务 |
| `ui` | 前端界面 |
| `config` | 配置相关 |

### 示例

```bash
# 新功能
git commit -m "feat(api): 添加对话历史导出接口"

# Bug 修复
git commit -m "fix(cache): 修复语义匹配阈值判断错误"

# 知识库更新
git commit -m "kb: 添加教务处服务指南文档"

# 破坏性变更
git commit -m "feat(api)!: 重构对话接口响应格式

BREAKING CHANGE: 响应格式从 {response: ...} 改为 {data: {answer: ...}}
迁移指南见 docs/migration/v2.md"
```

---

## 分支管理

### 分支命名

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| 主分支 | `main` | `main` |
| 功能分支 | `feature/<name>` | `feature/voice-input` |
| 修复分支 | `fix/<name>` | `fix/cache-bug` |
| 文档分支 | `docs/<name>` | `docs/api-reference` |
| 发布分支 | `release/<version>` | `release/v1.2.0` |
| 热修复分支 | `hotfix/<name>` | `hotfix/security-patch` |

### 分支工作流

```
main (稳定版本)
  |
  +--- develop (开发分支)
  |      |
  |      +--- feature/xxx (功能分支)
  |      +--- fix/xxx (修复分支)
  |
  +--- release/v1.x (发布分支)
  |
  +--- hotfix/xxx (热修复分支)
```

### 分支规则

1. **main 分支**：始终处于可发布状态，禁止直接推送
2. **feature 分支**：从 develop 分支创建，完成后合并回 develop
3. **release 分支**：准备发布时从 develop 创建
4. **hotfix 分支**：紧急修复从 main 创建，修复后合并到 main 和 develop

---

## Pull Request 流程

### PR 提交前检查清单

- [ ] 代码通过所有测试 (`pytest tests/`)
- [ ] 代码符合风格规范 (`black --check .` 和 `flake8 .`)
- [ ] 新功能有对应的测试用例
- [ ] 更新了相关文档
- [ ] 提交消息符合 Conventional Commits 规范
- [ ] 没有引入新的 lint 警告

### PR 标题格式

PR 标题应遵循与提交消息相同的格式：

```
feat: 添加语音输入功能
fix: 修复缓存语义匹配问题
docs: 更新 API 文档
```

### PR 描述模板

```markdown
## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 重构
- [ ] 其他

## 变更描述
<!-- 简要描述本次变更的内容和原因 -->

## 相关 Issue
<!-- 关联的 Issue 编号，如: Closes #123 -->

## 测试
<!-- 描述如何测试这些变更 -->

## 截图
<!-- 如有 UI 变更，附上截图 -->

## 检查清单
- [ ] 代码通过测试
- [ ] 新功能有文档说明
- [ ] 遵循代码规范
```

### 审核流程

1. 提交 PR 后，等待维护者审核
2. 根据审核意见修改代码
3. 至少需要 1 位审核者批准
4. 所有 CI 检查通过后可合并

---

## 知识库贡献指南

知识库是本项目的核心资产，我们欢迎校园相关内容的贡献。

### 知识库目录结构

```
data/knowledge_base/
├── FAQ/                  # 常见问题解答
├── 教务信息/             # 教务相关
├── 生活服务/             # 生活服务指南
├── 新生服务/             # 新生入学指南
├── 校园服务/             # 校园服务
├── 校园组织/             # 社团组织
├── 校规制度/             # 规章制度
├── 奖助学金/             # 奖助学金信息
├── 就业创业/             # 就业创业服务
├── 图书馆服务/           # 图书馆相关
└── 学校概况/             # 学校介绍
```

### 文档格式要求

#### Markdown 文档

```markdown
# 文档标题

> 一句话概述文档内容

## 基本信息

| 项目 | 内容 |
|------|------|
| 服务部门 | 教务处 |
| 联系电话 | 0731-xxxxxxxx |
| 办公地点 | xx楼xx室 |

## 详细说明

### 服务时间
周一至周五 8:00-12:00, 14:30-17:30

### 办理流程
1. 步骤一
2. 步骤二
3. 步骤三

## 相关链接
- [相关网站](url)

## 注意事项
- 注意事项一
- 注意事项二
```

#### FAQ 文档

```markdown
# 常见问题FAQ

## Q1: 图书馆开放时间？
A: 周一至周日 8:00-22:00，节假日另行通知。

## Q2: 如何办理在读证明？
A: 携带学生证到教务处办理，或通过网上办事大厅在线申请。
```

### 内容规范

1. **准确性**：信息必须来源可靠，标注信息来源
2. **时效性**：注明信息更新时间
3. **完整性**：包含必要的联系方式、办理流程
4. **格式统一**：遵循现有文档格式

### 知识库贡献流程

1. 在 `data/knowledge_base/` 对应目录创建或修改 Markdown 文件
2. 确保文件名为中文，清晰描述内容
3. 运行文档处理脚本：

```bash
python scripts/process_documents.py
```

4. 测试检索效果：

```bash
# 启动服务
python backend/main.py

# 测试检索
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你添加的问题", "session_id": "test"}'
```

---

## 问题反馈

### Bug 报告

如果你发现了 Bug，请通过 [GitHub Issues](https://github.com/your-repo/campus_helper/issues) 提交，包含以下信息：

```markdown
## Bug 描述
<!-- 清晰描述 Bug 的表现 -->

## 复现步骤
1. 步骤一
2. 步骤二
3. ...

## 期望行为
<!-- 描述你期望发生什么 -->

## 实际行为
<!-- 描述实际发生了什么 -->

## 环境信息
- 操作系统: Windows 11 / macOS / Linux
- Python 版本: 3.x.x
- Node.js 版本: x.x.x
- 浏览器: Chrome x.x.x

## 日志/截图
<!-- 如有相关日志或截图，请附上 -->
```

### 功能建议

```markdown
## 功能描述
<!-- 清晰描述你希望添加的功能 -->

## 使用场景
<!-- 描述这个功能解决什么问题 -->

## 建议实现
<!-- 如果有实现思路，请描述 -->
```

### 提问前

在提交 Issue 前，请：

1. 搜索现有 Issues，确认问题未被报告
2. 阅读文档和 FAQ
3. 尝试在最新版本中复现问题

---

## 获取帮助

- **GitHub Issues**: 提交 Bug 报告或功能建议
- **文档**: 查看 [README.md](README.md) 和 [USAGE.md](USAGE.md)
- **API 文档**: 启动服务后访问 http://localhost:8000/docs

---

再次感谢你对校园百事通项目的贡献！
