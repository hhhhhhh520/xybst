"""
LLM服务 - 封装不同LLM提供商的调用
"""
from typing import List, Dict, Any, Optional
import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from core.config import settings
from core.logger import logger


class LLMService:
    """大语言模型服务"""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.openai_client = None
        self.anthropic_client = None
        self.zhipu_client = None

        if self.provider == "openai":
            self.openai_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
        elif self.provider == "anthropic":
            self.anthropic_client = AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
        elif self.provider == "zhipu":
            # 智谱AI使用OpenAI兼容接口
            self.zhipu_client = AsyncOpenAI(
                api_key=settings.ZHIPU_API_KEY,
                base_url="https://open.bigmodel.cn/api/paas/v4/",
                timeout=120.0
            )
            logger.info(f"智谱AI客户端初始化完成，模型: {settings.ZHIPU_MODEL}")

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

        try:
            if self.provider == "openai":
                return await self._call_openai(system_prompt, user_prompt, history)
            elif self.provider == "anthropic":
                return await self._call_anthropic(system_prompt, user_prompt, history)
            elif self.provider == "zhipu":
                return await self._call_zhipu(system_prompt, user_prompt, history)
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

        response = await self.openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
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

        response = await self.anthropic_client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            system=system_prompt,
            messages=messages,
            max_tokens=1000
        )

        return response.content[0].text

    async def _call_zhipu(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        """调用智谱AI API（OpenAI兼容接口）"""
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history:
                role = msg.get("role", "user")
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })

        messages.append({"role": "user", "content": user_prompt})

        logger.info(f"调用智谱AI，模型: {settings.ZHIPU_MODEL}, 消息数: {len(messages)}")

        try:
            response = await self.zhipu_client.chat.completions.create(
                model=settings.ZHIPU_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            logger.info("智谱AI调用成功")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"智谱AI调用失败: {e}")
            raise

    async def _call_local(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """调用本地模型（Ollama）"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.LOCAL_MODEL_URL}/api/generate",
                json={
                    "model": settings.LOCAL_MODEL_NAME,
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

        return await self._call_zhipu(system_prompt, user_prompt)

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
