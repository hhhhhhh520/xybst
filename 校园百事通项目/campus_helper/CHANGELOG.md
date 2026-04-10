# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
