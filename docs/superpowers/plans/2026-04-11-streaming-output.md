# 流式输出功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为校园百事通添加SSE流式输出功能，让AI回答实时显示

**Architecture:** 后端使用FastAPI的StreamingResponse返回SSE格式数据，前端使用fetch + ReadableStream接收并实时渲染

**Tech Stack:** FastAPI SSE, fetch ReadableStream, AbortController

---

## 文件结构

```
backend/
├── services/
│   ├── llm_service.py      # 新增流式生成方法
│   └── agent_workflow.py   # 新增流式处理方法
├── api/
│   └── routes.py           # 修改/chat接口
frontend/
└── index.html              # 修改前端接收逻辑
```

---

### Task 1: 后端 - 添加LLM流式生成方法

**Files:**
- Modify: `D:/my project/xybst/校园百事通项目/campus_helper/backend/services/llm_service.py`

- [ ] **Step 1: 在LLMService类中添加流式生成方法**

在 `llm_service.py` 文件末尾，`LLMService` 类中添加以下方法：

```python
async def generate_answer_stream(
    self,
    query: str,
    context: str,
    history: Optional[List[Dict]] = None
):
    """
    流式生成答案

    Args:
        query: 用户问题
        context: 检索上下文
        history: 对话历史

    Yields:
        str: SSE格式的数据块
    """
    import json

    # 构建系统提示词
    system_prompt = """你是"小百"，校园百事通AI助手，专门为师生提供校园信息咨询服务。

你的回答必须基于提供的参考资料，不要编造信息。
回答结构：
1. 直接回答（1-2句话）
2. 详细说明（如有必要）
3. 下一步建议

重要信息（时间、地点、材料等）请用**加粗**标注。
"""

    # 构建用户提示词
    user_prompt = f"""参考资料：
{context}

用户问题：{query}

请基于参考资料回答用户问题。如果参考资料不足以回答问题，请明确说明。"""

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        for msg in history:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({
                "role": role,
                "content": msg.get("content", "")
            })

    messages.append({"role": "user", "content": user_prompt})

    provider_config = new_settings.llm.providers.get(self.provider)
    model = provider_config.model if provider_config else "deepseek-chat"

    try:
        # 使用流式调用
        stream = await self.llm_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'type': 'chunk', 'content': content}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"流式生成失败: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
```

- [ ] **Step 2: 提交代码**

```bash
cd "D:/my project/xybst"
git add "校园百事通项目/campus_helper/backend/services/llm_service.py"
git commit -m "feat: 添加LLM流式生成方法"
```

---

### Task 2: 后端 - 添加Agent工作流流式处理

**Files:**
- Modify: `D:/my project/xybst/校园百事通项目/campus_helper/backend/services/agent_workflow.py`

- [ ] **Step 1: 在AgentWorkflow类中添加流式处理方法**

在 `agent_workflow.py` 文件的 `AgentWorkflow` 类中，在 `process` 方法后添加：

```python
async def process_stream(
    self,
    query: str,
    session_id: str,
    user_id: str,
    user_info: Optional[Dict] = None
):
    """
    流式处理用户输入

    Args:
        query: 用户输入
        session_id: 会话ID
        user_id: 用户ID
        user_info: 用户信息（可选）

    Yields:
        str: SSE格式的数据块
    """
    import json

    # 获取对话状态
    state = self.get_or_create_session(session_id, user_id)
    state.updated_at = datetime.now()

    # 记录历史
    state.history.append({
        "role": "user",
        "content": query,
        "timestamp": datetime.now().isoformat()
    })

    # 发送开始信号
    yield f"data: {json.dumps({'type': 'start', 'session_id': session_id}, ensure_ascii=False)}\n\n"

    # 1. 意图识别
    intent, confidence = await IntentClassifier.classify_with_llm(query, self.llm)
    state.intent = intent
    state.intent_confidence = confidence
    logger.info(f"意图识别: {intent.value} (置信度: {confidence:.2f})")

    # 2. 槽位提取
    new_slots = SlotFiller.extract_slots(query, state.intent)
    state.filled_slots.update(new_slots)

    # 3. 根据意图执行对应工作流
    if state.intent == IntentType.KNOWLEDGE_QA:
        async for chunk in self._handle_knowledge_qa_stream(query, state):
            yield chunk
    elif state.intent == IntentType.CHITCHAT:
        # 闲聊直接返回
        response = await self._handle_chitchat(query, state)
        yield f"data: {json.dumps({'type': 'chunk', 'content': response['answer']}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'sources': [], 'cached': False}, ensure_ascii=False)}\n\n"
    else:
        # 其他类型按知识问答处理
        async for chunk in self._handle_knowledge_qa_stream(query, state):
            yield chunk

    # 记录助手回复（流式结束后）
    # 这里需要累积完整答案，简化处理

async def _handle_knowledge_qa_stream(
    self,
    query: str,
    state: DialogueState
):
    """流式处理知识问答"""
    import json

    # 获取缓存实例
    cache = get_cache()
    intent_str = IntentType.KNOWLEDGE_QA.value

    # 1. 尝试从缓存获取答案
    cached_entry = cache.get(query, embedding=None, intent=intent_str)

    if cached_entry:
        logger.info(f"[知识问答] 缓存命中，返回SSE格式")
        # 缓存命中，用SSE格式返回完整答案
        yield f"data: {json.dumps({'type': 'chunk', 'content': cached_entry.answer}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'sources': cached_entry.sources, 'cached': True}, ensure_ascii=False)}\n\n"
        return

    # 2. 缓存未命中，执行RAG检索
    retrieval_results = await retriever.retrieve(query)

    if not retrieval_results:
        # 无检索结果，返回兜底回复
        fallback = self._generate_fallback_response(query)
        yield f"data: {json.dumps({'type': 'chunk', 'content': fallback}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'sources': [], 'cached': False}, ensure_ascii=False)}\n\n"
        return

    # 3. 构建上下文
    context = self._build_context(retrieval_results)

    # 4. 流式生成答案
    full_answer = ""
    async for chunk in self.llm.generate_answer_stream(
        query=query,
        context=context,
        history=state.history[-6:]
    ):
        yield chunk
        # 累积答案
        if chunk.startswith("data: "):
            try:
                data = json.loads(chunk[6:].strip())
                if data.get("type") == "chunk":
                    full_answer += data.get("content", "")
            except:
                pass

    # 5. 提取来源
    sources = [
        {
            "title": r.metadata.get("title", "未知来源"),
            "score": round(r.score, 3)
        }
        for r in retrieval_results[:3]
    ]

    # 6. 发送结束信号
    yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'cached': False}, ensure_ascii=False)}\n\n"

    # 7. 存入缓存
    if full_answer:
        cache.set(
            query=query,
            answer=full_answer,
            sources=sources,
            embedding=None,
            intent=intent_str
        )
```

- [ ] **Step 2: 提交代码**

```bash
cd "D:/my project/xybst"
git add "校园百事通项目/campus_helper/backend/services/agent_workflow.py"
git commit -m "feat: 添加Agent工作流流式处理方法"
```

---

### Task 3: 后端 - 修改API接口返回流式响应

**Files:**
- Modify: `D:/my project/xybst/校园百事通项目/campus_helper/backend/api/routes.py`

- [ ] **Step 1: 修改chat接口为流式响应**

将 `routes.py` 中的 `chat` 函数替换为：

```python
from fastapi.responses import StreamingResponse

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    对话接口（流式输出）

    - **message**: 用户消息
    - **session_id**: 会话ID
    - **user_id**: 用户ID
    - **user_info**: 用户信息（可选）
    """
    return StreamingResponse(
        workflow.process_stream(
            query=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            user_info=request.user_info
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

- [ ] **Step 2: 提交代码**

```bash
cd "D:/my project/xybst"
git add "校园百事通项目/campus_helper/backend/api/routes.py"
git commit -m "feat: 修改chat接口为SSE流式响应"
```

---

### Task 4: 前端 - 修改接收逻辑支持流式输出

**Files:**
- Modify: `D:/my project/xybst/校园百事通项目/campus_helper/frontend/index.html`

- [ ] **Step 1: 修改sendMessage函数**

找到 `sendMessage` 函数（约1097行），替换为：

```javascript
// Send Message (流式版本)
let abortController = null;
let currentMessageDiv = null;

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Hide welcome screen
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }

    // Add user message
    addMessage(message, 'user');
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;

    // 创建AbortController用于取消请求
    abortController = new AbortController();

    // 创建助手消息容器
    currentMessageDiv = createStreamingMessage();

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                user_id: userId
            }),
            signal: abortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let sources = [];
        let cached = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'chunk') {
                            fullText += data.content;
                            updateStreamingMessage(currentMessageDiv, fullText);
                        } else if (data.type === 'done') {
                            sources = data.sources || [];
                            cached = data.cached || false;
                        } else if (data.type === 'error') {
                            updateStreamingMessage(currentMessageDiv, '抱歉，生成答案时出错：' + data.message);
                        }
                    } catch (e) {
                        console.error('解析SSE失败:', e);
                    }
                }
            }
        }

        // 流结束，最终渲染Markdown
        finalizeMessage(currentMessageDiv, fullText, sources, cached);

        // 保存到历史
        saveChatToHistory(message, fullText);

    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('用户取消了请求');
        } else {
            updateStreamingMessage(currentMessageDiv, '抱歉，服务暂时不可用，请确认后端服务已启动');
            showToast('服务连接失败', 'error');
        }
    }

    sendBtn.disabled = false;
    abortController = null;
    currentMessageDiv = null;
}
```

- [ ] **Step 2: 添加流式消息相关函数**

在 `sendMessage` 函数后添加：

```javascript
// 创建流式消息容器
function createStreamingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-avatar">🎓</div>
        <div class="message-body">
            <div class="message-content">
                <span class="streaming-cursor">|</span>
            </div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 添加光标闪烁动画
    const cursor = messageDiv.querySelector('.streaming-cursor');
    cursor.style.animation = 'blink 1s infinite';

    return messageDiv;
}

// 更新流式消息内容
function updateStreamingMessage(messageDiv, content) {
    const contentEl = messageDiv.querySelector('.message-content');
    contentEl.innerHTML = formatContent(content) + '<span class="streaming-cursor">|</span>';

    // 保持光标闪烁
    const cursor = contentEl.querySelector('.streaming-cursor');
    if (cursor) {
        cursor.style.animation = 'blink 1s infinite';
    }

    // 滚动到底部
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 完成消息渲染
function finalizeMessage(messageDiv, content, sources, cached) {
    const contentEl = messageDiv.querySelector('.message-content');

    // 移除光标，渲染最终Markdown
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                来源: ${sources.map(s => s.title).join(', ')}
                ${cached ? '<span style="color: var(--success-color); margin-left: 8px;">(缓存)</span>' : ''}
            </div>
        `;
    }

    contentEl.innerHTML = formatContent(content) + sourcesHtml;

    // 添加操作按钮
    const actionsHtml = `
        <div class="message-actions">
            <button class="message-action-btn" onclick="copyMessage(this)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                复制
            </button>
        </div>
    `;

    messageDiv.querySelector('.message-body').insertAdjacentHTML('beforeend', actionsHtml);
}

// 停止生成
function stopGeneration() {
    if (abortController) {
        abortController.abort();
    }
}
```

- [ ] **Step 3: 添加光标闪烁CSS动画**

在 `<style>` 标签中添加：

```css
@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

.streaming-cursor {
    color: var(--accent-primary);
    font-weight: bold;
}
```

- [ ] **Step 4: 提交代码**

```bash
cd "D:/my project/xybst"
git add "校园百事通项目/campus_helper/frontend/index.html"
git commit -m "feat: 前端支持SSE流式输出"
```

---

### Task 5: 测试流式输出功能

- [ ] **Step 1: 启动后端服务**

```bash
cd "D:/my project/xybst/校园百事通项目/campus_helper"
python backend/main.py
```

- [ ] **Step 2: 打开前端页面**

浏览器访问 `http://localhost:8000`

- [ ] **Step 3: 测试流式输出**

发送问题："奖学金怎么申请？"
预期：答案逐字显示，有闪烁光标

- [ ] **Step 4: 测试缓存命中**

再次发送相同问题："奖学金怎么申请？"
预期：答案快速返回（缓存命中），但仍使用SSE格式

- [ ] **Step 5: 提交最终版本**

```bash
cd "D:/my project/xybst"
git add .
git commit -m "feat: 完成流式输出功能"
```
