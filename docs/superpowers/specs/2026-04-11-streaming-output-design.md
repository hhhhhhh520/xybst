# 流式输出功能设计

> 日期: 2026-04-11

## 概述

为校园百事通项目添加流式输出功能，让AI回答实时显示，提升用户体验。

## 需求

- LLM生成答案时，逐字实时显示
- 缓存命中时，统一使用SSE格式返回（单个chunk）
- 支持用户主动取消生成
- Markdown延迟渲染（累积全文后重新渲染）

## 架构

```
用户提问
    ↓
前端 fetch('/api/chat', signal: abortController.signal)
    ↓
后端检查缓存
    ├── 命中 → SSE返回（start → chunk(完整内容) → done）
    └── 未命中 → 调用LLM流式 → SSE逐chunk返回
    ↓
前端接收SSE
    ├── 收到chunk → 累积全文 → 重新渲染Markdown
    └── 用户点击停止 → abortController.abort()
    ↓
流结束 → 显示来源信息
```

## SSE 消息格式

```json
// 开始
data: {"type": "start", "session_id": "xxx"}

// 内容块（可能多次）
data: {"type": "chunk", "content": "部分内容"}

// 结束
data: {"type": "done", "sources": [...], "cached": false}

// 错误
data: {"type": "error", "message": "xxx"}
```

## 改动文件

### 后端

1. **backend/services/llm_service.py**
   - 新增 `generate_answer_stream()` 方法
   - 使用 `stream=True` 调用LLM API
   - 逐chunk yield返回

2. **backend/services/agent_workflow.py**
   - 修改 `process()` 方法
   - 缓存命中时返回SSE格式
   - 未命中时调用流式生成

3. **backend/api/routes.py**
   - 修改 `/chat` 接口返回 `StreamingResponse`
   - media_type=`text/event-stream`

### 前端

1. **frontend/index.html**
   - 修改 `sendMessage()` 使用fetch + ReadableStream
   - 添加 `AbortController` 支持取消
   - 累积全文后重新渲染Markdown
   - 添加"停止生成"按钮

## 错误处理

- LLM调用失败 → 返回error类型的SSE消息
- 前端连接中断 → 显示"连接中断，请重试"
- 用户取消 → abortController.abort()
- 超时 → 30秒无响应断开

## 测试要点

1. 正常流式输出
2. 缓存命中时的SSE返回
3. 用户取消生成
4. 网络错误处理
5. Markdown渲染正确性
