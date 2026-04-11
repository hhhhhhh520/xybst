"""
LLM服务 - 封装不同LLM提供商的调用
"""
from typing import List, Dict, Any, Optional
import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from core.config import settings, new_settings
from core.logger import logger


class LLMService:
    """大语言模型服务"""

    def __init__(self):
        self.provider = new_settings.llm.provider
        self.openai_client = None
        self.anthropic_client = None
        self.llm_client = None  # 通用客户端（用于智谱、DeepSeek等OpenAI兼容接口）

        if self.provider == "openai":
            provider_config = new_settings.llm.providers.get("openai")
            if provider_config:
                self.openai_client = AsyncOpenAI(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url
                )
        elif self.provider == "anthropic":
            provider_config = new_settings.llm.providers.get("anthropic")
            if provider_config:
                self.anthropic_client = AsyncAnthropic(
                    api_key=provider_config.api_key
                )
        elif self.provider in ["zhipu", "deepseek"]:
            provider_config = new_settings.llm.providers.get(self.provider)
            if provider_config:
                # 智谱AI和DeepSeek使用OpenAI兼容接口
                self.llm_client = AsyncOpenAI(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url,
                    timeout=getattr(provider_config, 'timeout', 120.0)
                )
                logger.info(f"{self.provider}客户端初始化完成，模型: {provider_config.model}")

    async def generate_answer(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        """
        生成答案

        Args:
            query: 用户问题
            context: 检索上下文
            history: 对话历史

        Returns:
            生成的答案
        """
        # 构建系统提示词（完整版本）
        system_prompt = """# 角色设定
你是"小百"，湖南农业大学的官方AI助手，专门为师生提供校园信息咨询服务。
你的形象是一位22岁的优秀学长/学姐，熟悉学校的方方面面，热心帮助学弟学妹解决问题。

## 核心能力
1. 准确回答关于教务、学工、后勤、就业等各类校园事务的咨询
2. 帮助师生快速找到办事流程、政策文件、联系方式
3. 根据用户身份（学生/教师、年级、专业）提供个性化信息
4. 在无法确定答案时，引导用户至正确的部门或人工服务

## 回答规范

### 信息准确性（最重要）
- 必须基于知识库内容回答，绝对不得编造政策、时间、流程
- 涉及具体时间、地点、金额的信息，必须核对知识库原文
- 如知识库信息不足，明确告知："关于这个问题，我的信息可能不够完整，建议您："并提供相关部门联系方式
- 不确定时宁可说"不知道"，也不要猜测

### 回答结构（标准三段式）
1. **直接回答**：首先给出用户问题的核心答案（1-2句话）
2. **详细说明**：如有必要，补充具体细节、条件、流程
3. **操作指引**：告知用户下一步应该怎么做，提供 actionable 的建议

### 语言风格
- 对学生：使用"同学"称呼，语气亲切自然，适当使用表情符号
- 对教师：使用"老师"称呼，语气专业简洁
- 避免使用过于学术化或技术化的表达
- 重要信息（截止时间、必需材料等）用**加粗**标注
- 列表使用数字编号，清晰易读

### 安全与隐私（严格遵循）
- 绝不询问或存储用户的密码、银行卡号等敏感信息
- 涉及个人成绩、排名等隐私信息，需确认用户身份后才能提供
- 不传播未经证实的消息、谣言
- 遇到投诉或敏感问题，引导至正式渠道

## 边界情况处理

### 非校园问题
"这个问题超出了我的服务范围呢 😅 我是校园百事通小百，主要帮助解决教务、生活等校园相关问题。"

### 紧急情况
"这个情况比较紧急，建议您立即拨打相关部门电话或前往现场咨询，以免耽误您的事情。"
"""

        # 构建用户提示词
        user_prompt = f"""参考资料：
{context}

用户问题：{query}

请基于参考资料回答用户问题。如果参考资料不足以回答问题，请明确说明。"""

        try:
            if self.provider == "openai":
                return await self._call_openai(system_prompt, user_prompt, history)
            elif self.provider == "anthropic":
                return await self._call_anthropic(system_prompt, user_prompt, history)
            elif self.provider in ["zhipu", "deepseek"]:
                return await self._call_llm(system_prompt, user_prompt, history)
            else:
                return await self._call_local(system_prompt, user_prompt)

        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return "抱歉，系统暂时繁忙，请稍后再试。"

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        """调用OpenAI API"""
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })

        messages.append({"role": "user", "content": user_prompt})

        provider_config = new_settings.llm.providers.get("openai")
        max_tokens = provider_config.max_tokens if provider_config else 1000
        temperature = provider_config.temperature if provider_config else 0.7
        model = provider_config.model if provider_config else "gpt-3.5-turbo"

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        """调用Anthropic API"""
        messages = []

        if history:
            for msg in history:
                role = msg.get("role", "user")
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })

        messages.append({"role": "user", "content": user_prompt})

        provider_config = new_settings.llm.providers.get("anthropic")
        max_tokens = provider_config.max_tokens if provider_config else 1000
        model = provider_config.model if provider_config else "claude-3-sonnet-20240229"

        response = await self.anthropic_client.messages.create(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=max_tokens
        )

        return response.content[0].text

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        """调用LLM API（OpenAI兼容接口，支持智谱、DeepSeek等）"""
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history:
                role = msg.get("role", "user")
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })

        messages.append({"role": "user", "content": user_prompt})

        provider_config = new_settings.llm.providers.get(self.provider)
        max_tokens = provider_config.max_tokens if provider_config else 1000
        temperature = provider_config.temperature if provider_config else 0.7
        model = provider_config.model if provider_config else "deepseek-chat"

        logger.info(f"调用{self.provider}，模型: {model}, 消息数: {len(messages)}")

        try:
            response = await self.llm_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            logger.info(f"{self.provider}调用成功")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"{self.provider}调用失败: {e}")
            raise

    async def _call_local(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """调用本地模型（Ollama）"""
        provider_config = new_settings.llm.providers.get("local")
        url = provider_config.url if provider_config else "http://localhost:11434"
        model = provider_config.model if provider_config else "qwen:7b"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False
                }
            )
            result = response.json()
            return result.get("response", "")

    async def generate_guide(
        self,
        query: str,
        context: str,
        stage: str = "overview"
    ) -> str:
        """
        生成办事指南

        Args:
            query: 用户问题
            context: 检索上下文
            stage: 当前阶段

        Returns:
            生成的指南
        """
        system_prompt = """你是校园百事通小百，专门帮助师生办理各类校园事务。

请提供清晰、分步骤的办事指南：
1. 列出所需材料（使用checkbox格式）
2. 说明办理步骤
3. 标注重要时间节点
4. 提供相关部门联系方式

语气要友好、鼓励。"""

        user_prompt = f"""参考资料：
{context}

用户想办理：{query}
当前阶段：{stage}

请提供详细的办理指南。"""

        return await self._call_llm(system_prompt, user_prompt)

    async def rewrite_query(self, query: str) -> List[str]:
        """
        查询重写，扩展同义词

        Args:
            query: 原始查询

        Returns:
            重写后的查询列表
        """
        system_prompt = "你是一个查询优化助手，请将用户查询扩展为多个相关表达。"

        user_prompt = f"""将以下查询扩展为3-5个不同的表达方式：

查询：{query}

请以JSON数组格式输出扩展后的查询。"""

        try:
            response = await self._call_openai(system_prompt, user_prompt)
            # 简单解析，实际项目中应使用更健壮的JSON解析
            import json
            # 尝试提取JSON数组
            if "[" in response and "]" in response:
                start = response.find("[")
                end = response.rfind("]") + 1
                queries = json.loads(response[start:end])
                return queries
        except Exception as e:
            logger.error(f"查询重写失败: {e}")

        return [query]

    async def rewrite_query_with_context(
        self,
        query: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        """
        根据对话历史重写查询，将简短回答转换为完整查询

        Args:
            query: 用户当前输入
            history: 对话历史

        Returns:
            重写后的查询（如果需要重写）或原始查询
        """
        if not history or len(history) < 2:
            return query

        # 检查是否是简短回答（可能是对追问的回复）
        if len(query) > 15:
            # 较长的输入通常已经是完整问题
            return query

        # 构建重写提示词
        system_prompt = """你是一个对话理解助手，专门分析用户回答与上下文的关系。

你的任务是判断用户的当前输入是否是对之前AI追问的回答，如果是，则将其重写为完整的查询。

重写规则：
1. 如果用户输入是简短回答（如"本科"、"研究生"、"大一"等），且之前的AI回复包含追问，则结合追问重写
2. 保持用户原意，不要添加额外信息
3. 如果用户的输入本身就是一个完整问题，则原样返回
4. 只输出重写后的查询，不要其他解释

示例：
历史：[用户: 奖学金怎么申请？, AI: ...你是本科生还是研究生？]
用户输入：本科
重写结果：本科生奖学金怎么申请

历史：[用户: 图书馆几点开门？, AI: 图书馆开放时间是...]
用户输入：谢谢
重写结果：谢谢（无需重写，这是闲聊）

历史：[用户: 选课流程是什么？, AI: ...你想了解哪种类型的选课？（必修/选修）]
用户输入：选修课
重写结果：选修课选课流程是什么"""

        # 构建历史摘要
        history_text = ""
        for msg in history[-4:]:  # 最近2轮对话
            role = "用户" if msg.get("role") == "user" else "AI"
            content = msg.get("content", "")[:200]  # 截断长内容
            history_text += f"{role}: {content}\n"

        user_prompt = f"""对话历史：
{history_text}

用户当前输入：{query}

请判断用户输入是否需要结合上下文重写，如果需要则输出重写后的查询，否则原样返回。"""

        try:
            response = await self._call_llm(system_prompt, user_prompt)
            rewritten = response.strip()

            # 如果重写结果与原查询差异较大，说明进行了重写
            if rewritten and rewritten != query:
                logger.info(f"[查询重写] '{query}' -> '{rewritten}'")
                return rewritten

        except Exception as e:
            logger.warning(f"上下文查询重写失败: {e}")

        return query

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

        # 构建系统提示词（完整版本）
        system_prompt = """# 角色设定
你是"小百"，湖南农业大学的官方AI助手，专门为师生提供校园信息咨询服务。
你的形象是一位22岁的优秀学长/学姐，熟悉学校的方方面面，热心帮助学弟学妹解决问题。

## 核心能力
1. 准确回答关于教务、学工、后勤、就业等各类校园事务的咨询
2. 帮助师生快速找到办事流程、政策文件、联系方式
3. 根据用户身份（学生/教师、年级、专业）提供个性化信息
4. 在无法确定答案时，引导用户至正确的部门或人工服务

## 回答规范

### 信息准确性（最重要）
- 必须基于知识库内容回答，绝对不得编造政策、时间、流程
- 涉及具体时间、地点、金额的信息，必须核对知识库原文
- 如知识库信息不足，明确告知："关于这个问题，我的信息可能不够完整，建议您："并提供相关部门联系方式
- 不确定时宁可说"不知道"，也不要猜测

### 回答结构（标准三段式）
1. **直接回答**：首先给出用户问题的核心答案（1-2句话）
2. **详细说明**：如有必要，补充具体细节、条件、流程
3. **操作指引**：告知用户下一步应该怎么做，提供 actionable 的建议

### 语言风格
- 对学生：使用"同学"称呼，语气亲切自然，适当使用表情符号
- 对教师：使用"老师"称呼，语气专业简洁
- 避免使用过于学术化或技术化的表达
- 重要信息（截止时间、必需材料等）用**加粗**标注
- 列表使用数字编号，清晰易读

### 安全与隐私（严格遵循）
- 绝不询问或存储用户的密码、银行卡号等敏感信息
- 涉及个人成绩、排名等隐私信息，需确认用户身份后才能提供
- 不传播未经证实的消息、谣言
- 遇到投诉或敏感问题，引导至正式渠道

## 边界情况处理

### 非校园问题
"这个问题超出了我的服务范围呢 😅 我是校园百事通小百，主要帮助解决教务、生活等校园相关问题。"

### 紧急情况
"这个情况比较紧急，建议您立即拨打相关部门电话或前往现场咨询，以免耽误您的事情。"
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
