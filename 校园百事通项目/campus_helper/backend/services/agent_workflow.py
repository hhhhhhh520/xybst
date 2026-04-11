"""
Agent工作流引擎 - 意图识别、对话管理、任务执行
"""
import json
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from core.config import settings
from core.logger import logger
from services.llm_service import LLMService
from services.rag_retriever import retriever
from services.answer_cache import get_cache


class IntentType(Enum):
    """意图类型"""
    KNOWLEDGE_QA = "knowledge_qa"      # 知识问答
    PERSONAL_QUERY = "personal_query"  # 个人查询
    AFFAIR_GUIDE = "affair_guide"      # 事务办理
    CHITCHAT = "chitchat"              # 闲聊
    UNKNOWN = "unknown"                # 未知


@dataclass
class DialogueState:
    """对话状态"""
    session_id: str
    user_id: str
    intent: IntentType = IntentType.UNKNOWN
    intent_confidence: float = 0.0
    slots: Dict[str, Any] = field(default_factory=dict)
    filled_slots: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    current_step: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "intent": self.intent.value,
            "intent_confidence": self.intent_confidence,
            "slots": self.slots,
            "filled_slots": self.filled_slots,
            "history": self.history[-10:],  # 只保留最近10轮
            "current_step": self.current_step,
            "context": self.context
        }


class IntentClassifier:
    """意图分类器 - 混合策略：关键词 + LLM语义理解"""

    # 意图描述（用于LLM提示）
    INTENT_DESCRIPTIONS = {
        IntentType.KNOWLEDGE_QA: "知识问答：询问校园政策、规定、时间地点等一般信息",
        IntentType.PERSONAL_QUERY: "个人查询：查询个人课表、成绩、学分等私人信息",
        IntentType.AFFAIR_GUIDE: "事务办理：申请办理某项事务，如开证明、请假、转专业等",
        IntentType.CHITCHAT: "闲聊：打招呼、感谢、告别等日常对话"
    }

    # 高权重关键词（强特征）
    HIGH_WEIGHT_KEYWORDS = {
        IntentType.PERSONAL_QUERY: [
            "我的课表", "我的成绩", "我的学分", "我的绩点", "我考了多少",
            "查一下我", "帮我查", "查询我的", "本人成绩", "本人课表",
            "我的考试", "我的排名", "查我", "我看下"
        ],
        IntentType.AFFAIR_GUIDE: [
            "怎么办理", "如何办理", "办理流程", "申请流程", "怎么申请",
            "需要什么材料", "要准备什么", "去哪里办", "开证明", "办证明",
            "怎么办", "如何申请"
        ],
        IntentType.CHITCHAT: [
            "你好", "谢谢", "再见", "拜拜", "早上好", "下午好", "晚上好",
            "在吗", "有人吗", "哈喽", "嗨", "你是谁", "你叫什么", "你是啥"
        ]
    }

    # 普通关键词
    KEYWORDS = {
        IntentType.KNOWLEDGE_QA: [
            # 疑问词
            "是什么", "怎么样", "如何", "怎么", "多少", "哪里", "什么时候", "几点",
            "能不能", "可以吗", "有吗", "是不是", "为什么",
            # 校园场所
            "图书馆", "食堂", "宿舍", "寝室", "教室", "操场", "体育馆", "医务室",
            "实验室", "行政楼", "教学楼", "实验楼",
            # 教务相关
            "成绩", "课表", "考试", "学分", "选课", "补考", "重修", "绩点",
            "四六级", "计算机二级", "普通话", "教师资格证",
            # 奖助相关
            "奖学金", "助学金", "资助", "补助", "贷款", "勤工助学",
            # 事务相关
            "证明", "流程", "政策", "规定", "请假", "销假",
            # 宿舍生活
            "门禁", "熄灯", "断电", "水电", "报修", "入住", "退宿", "换宿舍",
            # 就业相关
            "就业", "招聘", "实习", "求职", "校招", "春招", "秋招",
            # 新生相关
            "新生", "报到", "军训", "迎新",
            # 学校概况
            "学校", "历史", "简介", "概况", "特色", "专业", "学院", "校训",
            "成立", "创办", "荣誉", "排名", "师资", "学科", "ESI",
            # 图书馆服务
            "借阅", "借书", "还书", "续借", "图书", "阅览", "座位",
            # 其他
            "时间", "地点", "电话", "地址", "费用", "条件", "要求", "截止"
        ],
        IntentType.PERSONAL_QUERY: [
            "课表", "成绩", "学分", "绩点", "排名", "考勤", "考试安排",
            "已修", "未修", "必修", "选修"
        ],
        IntentType.AFFAIR_GUIDE: [
            "申请", "办理", "请假", "转专业", "休学", "复学", "退学",
            "毕业", "档案", "户口", "证明", "证书"
        ],
        IntentType.CHITCHAT: [
            "你好", "谢谢", "再见", "在吗", "哈喽", "嗨"
        ]
    }

    # 排除词（避免误分类）
    EXCLUSION_RULES = {
        IntentType.CHITCHAT: ["怎么", "如何", "什么", "哪"],  # 包含这些词的不是纯闲聊
    }

    @classmethod
    def classify(cls, query: str, llm_service: Optional[Any] = None) -> tuple:
        """
        意图分类 - 混合策略

        Args:
            query: 用户输入
            llm_service: LLM服务实例（可选，用于语义理解）

        Returns:
            (意图类型, 置信度)
        """
        query_lower = query.lower().strip()
        # 使用 repr 避免编码问题
        logger.info(f"[意图分类] 输入查询长度: {len(query_lower)}, 内容: {repr(query_lower[:50])}")

        # 1. 先检查高权重关键词（强特征，直接返回）
        for intent, keywords in cls.HIGH_WEIGHT_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    logger.info(f"[意图分类] 高权重关键词匹配: {repr(kw)} -> {intent.value}")
                    return intent, 0.95

        # 2. 检查闲聊（优先处理简单问候）
        chitchat_score = cls._check_chitchat(query_lower)
        if chitchat_score > 0.8:
            return IntentType.CHITCHAT, chitchat_score

        # 3. 计算各意图得分
        scores = {}
        for intent, keywords in cls.KEYWORDS.items():
            if intent == IntentType.CHITCHAT:
                continue  # 已单独处理

            score = 0
            matched_keywords = []

            for kw in keywords:
                if kw in query_lower:
                    matched_keywords.append(kw)
                    # 根据关键词长度加权（越长越具体）
                    score += len(kw) / 10

            if score > 0:
                # 应用排除规则
                if intent in cls.EXCLUSION_RULES:
                    for exc_word in cls.EXCLUSION_RULES[intent]:
                        if exc_word in query_lower:
                            score *= 0.3  # 降低置信度

                scores[intent] = {
                    "score": score,
                    "matched": matched_keywords
                }

        # 4. 分析结果
        if not scores:
            # 无匹配，返回未知
            return IntentType.UNKNOWN, 0.3

        # 找出最佳匹配
        best_intent = max(scores.keys(), key=lambda x: scores[x]["score"])
        raw_score = scores[best_intent]["score"]

        # 计算置信度（归一化）
        confidence = min(0.5 + raw_score * 0.15, 0.92)

        # 5. 如果置信度不够高，标记为需要LLM辅助
        if confidence < 0.7 and llm_service:
            # 这里可以调用LLM进行语义理解
            # 暂时返回当前结果，后续可以优化
            pass

        return best_intent, confidence

    @classmethod
    def _check_chitchat(cls, query: str) -> float:
        """检查是否为闲聊"""
        chitchat_patterns = [
            ("你好", 0.95), ("谢谢", 0.95), ("再见", 0.95), ("拜拜", 0.95),
            ("在吗", 0.9), ("有人吗", 0.9), ("哈喽", 0.9), ("嗨", 0.9),
            ("早上好", 0.95), ("下午好", 0.95), ("晚上好", 0.95),
            ("你是谁", 0.85), ("你叫什么", 0.85), ("你是啥", 0.85)
        ]

        for pattern, score in chitchat_patterns:
            if pattern in query:
                # 检查是否只是简单问候（没有其他实质内容）
                if len(query) <= len(pattern) + 5:
                    return score

        return 0.0

    @classmethod
    async def classify_with_llm(
        cls,
        query: str,
        llm_service: Any
    ) -> tuple:
        """
        使用LLM进行意图分类（当关键词方法不确定时调用）

        Args:
            query: 用户输入
            llm_service: LLM服务实例

        Returns:
            (意图类型, 置信度)
        """
        # 先尝试关键词匹配
        intent, confidence = cls.classify(query)
        logger.info(f"[意图分类] 关键词匹配结果: {intent.value}, 置信度: {confidence}")

        # 如果置信度足够高，直接返回
        if confidence >= 0.7:
            logger.info(f"[意图分类] 置信度足够高，直接返回")
            return intent, confidence

        # 使用LLM进行语义理解
        logger.info(f"[意图分类] 置信度不足，调用LLM辅助分类")
        try:
            llm_result = await cls._llm_classify(query, llm_service)
            if llm_result:
                return llm_result
        except Exception as e:
            logger.warning(f"LLM意图分类失败: {e}")

        return intent, confidence

    @classmethod
    async def _llm_classify(cls, query: str, llm_service: Any) -> Optional[tuple]:
        """调用LLM进行意图分类"""
        import json

        prompt = f"""你是一个意图分类助手。请分析用户问题的意图。

用户问题：{query}

意图类型：
1. knowledge_qa - 询问校园信息（政策、时间、地点、流程等公共信息）
2. personal_query - 查询个人数据（课表、成绩、学分、考试安排等私人信息）
3. affair_guide - 办理具体事务（开证明、请假、转专业等需要操作的事务）
4. chitchat - 日常对话（打招呼、感谢、告别等简单问候）

重要判断规则：
- 包含"我的" + 数据类型（课表/成绩/学分/考试）→ personal_query（不是 chitchat！）
- 包含"是什么"、"怎么"、"如何" + 校园相关词 → knowledge_qa
- 包含"办理"、"申请"、"怎么办理" → affair_guide
- 只有简单问候语（你好、谢谢、再见）→ chitchat

示例：
- "我的课表是什么" → personal_query（包含"我的"+"课表"）
- "图书馆开放时间" → knowledge_qa
- "怎么办理在读证明" → affair_guide
- "你好" → chitchat

返回JSON：{{"intent": "意图类型名称", "confidence": 0.9}}

只返回JSON，不要其他内容。"""

        try:
            # 调用LLM
            if hasattr(llm_service, '_call_zhipu'):
                response = await llm_service._call_zhipu(
                    "你是一个意图分类助手，请准确判断用户意图。",
                    prompt
                )

                logger.info(f"[LLM意图分类] 原始响应: {response}")

                # 解析JSON
                if "{" in response and "}" in response:
                    start = response.find("{")
                    end = response.rfind("}") + 1
                    json_str = response[start:end]
                    logger.info(f"[LLM意图分类] JSON字符串: {json_str}")
                    result = json.loads(json_str)

                    intent_str = result.get("intent", "unknown")
                    confidence = result.get("confidence", 0.5)

                    # 映射到IntentType（支持数字和字符串两种格式）
                    intent_map = {
                        "knowledge_qa": IntentType.KNOWLEDGE_QA,
                        "personal_query": IntentType.PERSONAL_QUERY,
                        "affair_guide": IntentType.AFFAIR_GUIDE,
                        "chitchat": IntentType.CHITCHAT,
                        "1": IntentType.KNOWLEDGE_QA,
                        "2": IntentType.PERSONAL_QUERY,
                        "3": IntentType.AFFAIR_GUIDE,
                        "4": IntentType.CHITCHAT
                    }

                    intent = intent_map.get(intent_str, IntentType.UNKNOWN)
                    logger.info(f"LLM意图分类: {intent.value} (置信度: {confidence})")
                    return intent, confidence

        except Exception as e:
            logger.error(f"LLM意图分类异常: {e}")

        return None


class SlotFiller:
    """槽位填充器"""

    # 定义各意图需要的槽位
    REQUIRED_SLOTS = {
        IntentType.PERSONAL_QUERY: ["query_type", "semester"],
        IntentType.AFFAIR_GUIDE: ["affair_type"]
    }

    @classmethod
    def extract_slots(cls, query: str, intent: IntentType) -> Dict[str, Any]:
        """从查询中提取槽位"""
        slots = {}

        # 提取学期信息
        semester_patterns = [
            r"(20\d{2})-?(20\d{2})?[-\s]?(\d)",  # 2024-2025-1
            r"(本|上|下)学期",
            r"(大一|大二|大三|大四)[上下]"
        ]
        for pattern in semester_patterns:
            match = re.search(pattern, query)
            if match:
                slots["semester"] = match.group(0)
                break

        # 提取查询类型
        if intent == IntentType.PERSONAL_QUERY:
            if "课表" in query or "课程" in query:
                slots["query_type"] = "schedule"
            elif "成绩" in query:
                slots["query_type"] = "grades"
            elif "考试" in query:
                slots["query_type"] = "exams"
            elif "学分" in query:
                slots["query_type"] = "credits"

        # 提取事务类型
        if intent == IntentType.AFFAIR_GUIDE:
            affair_keywords = {
                "奖学金": "scholarship",
                "证明": "certificate",
                "请假": "leave",
                "转专业": "major_transfer",
                "毕业": "graduation"
            }
            for kw, value in affair_keywords.items():
                if kw in query:
                    slots["affair_type"] = value
                    break

        return slots

    @classmethod
    def check_missing_slots(
        cls,
        intent: IntentType,
        filled_slots: Dict[str, Any]
    ) -> List[str]:
        """检查缺失的槽位"""
        required = cls.REQUIRED_SLOTS.get(intent, [])
        missing = [slot for slot in required if slot not in filled_slots]
        return missing


class AgentWorkflow:
    """Agent工作流引擎"""

    def __init__(self):
        self.llm = LLMService()
        self.sessions: Dict[str, DialogueState] = {}

    def get_or_create_session(
        self,
        session_id: str,
        user_id: str
    ) -> DialogueState:
        """获取或创建对话状态"""
        if session_id not in self.sessions:
            self.sessions[session_id] = DialogueState(
                session_id=session_id,
                user_id=user_id
            )
        return self.sessions[session_id]

    async def process(
        self,
        query: str,
        session_id: str,
        user_id: str,
        user_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入

        Args:
            query: 用户输入
            session_id: 会话ID
            user_id: 用户ID
            user_info: 用户信息（可选）

        Returns:
            处理结果
        """
        # 获取对话状态
        state = self.get_or_create_session(session_id, user_id)
        state.updated_at = datetime.now()

        # 记录历史
        state.history.append({
            "role": "user",
            "content": query,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"处理用户输入 [{session_id}]: {query[:50]}...")

        # 0. 上下文查询重写 - 将简短回答转换为完整查询
        rewritten_query = await self.llm.rewrite_query_with_context(query, state.history)
        if rewritten_query != query:
            logger.info(f"[查询重写] 原始: '{query}' -> 重写: '{rewritten_query}'")
            query = rewritten_query

        # 1. 意图识别 - 使用混合策略（关键词 + LLM辅助）
        intent, confidence = await IntentClassifier.classify_with_llm(query, self.llm)
        state.intent = intent
        state.intent_confidence = confidence
        logger.info(f"意图识别: {intent.value} (置信度: {confidence:.2f})")

        # 2. 槽位提取
        new_slots = SlotFiller.extract_slots(query, state.intent)
        state.filled_slots.update(new_slots)
        logger.debug(f"📦 已填充槽位: {state.filled_slots}")

        # 3. 根据意图执行对应工作流
        if state.intent == IntentType.KNOWLEDGE_QA:
            response = await self._handle_knowledge_qa(query, state)
        elif state.intent == IntentType.PERSONAL_QUERY:
            response = await self._handle_personal_query(query, state, user_info)
        elif state.intent == IntentType.AFFAIR_GUIDE:
            response = await self._handle_affair_guide(query, state)
        elif state.intent == IntentType.CHITCHAT:
            response = await self._handle_chitchat(query, state)
        else:
            response = await self._handle_unknown(query, state)

        # 记录助手回复
        state.history.append({
            "role": "assistant",
            "content": response.get("answer", ""),
            "timestamp": datetime.now().isoformat()
        })

        return response

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

        # 0. 上下文查询重写 - 将简短回答转换为完整查询
        rewritten_query = await self.llm.rewrite_query_with_context(query, state.history)
        if rewritten_query != query:
            logger.info(f"[查询重写] 原始: '{query}' -> 重写: '{rewritten_query}'")
            query = rewritten_query

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

    async def _handle_knowledge_qa_stream(
        self,
        query: str,
        state: DialogueState
    ):
        """流式处理知识问答"""
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

    async def _handle_knowledge_qa(
        self,
        query: str,
        state: DialogueState
    ) -> Dict[str, Any]:
        """处理知识问答"""
        # 获取缓存实例
        cache = get_cache()

        # 1. 尝试从缓存获取答案
        intent_str = IntentType.KNOWLEDGE_QA.value
        cached_entry = cache.get(query, embedding=None, intent=intent_str)

        if cached_entry:
            logger.info(f"[知识问答] 缓存命中，直接返回答案")
            return {
                "answer": cached_entry.answer,
                "sources": cached_entry.sources,
                "type": "knowledge_qa",
                "cached": True
            }

        # 2. 缓存未命中，执行RAG检索
        retrieval_results = await retriever.retrieve(query)

        if not retrieval_results:
            # 无检索结果，兜底回复
            return {
                "answer": self._generate_fallback_response(query),
                "sources": [],
                "type": "fallback"
            }

        # 3. 构建上下文
        context = self._build_context(retrieval_results)

        # 4. 生成答案
        answer = await self.llm.generate_answer(
            query=query,
            context=context,
            history=state.history[-6:]  # 最近3轮对话
        )

        # 5. 提取来源
        sources = [
            {
                "title": r.metadata.get("title", "未知来源"),
                "score": round(r.score, 3)
            }
            for r in retrieval_results[:3]
        ]

        # 6. 存入缓存
        cache.set(
            query=query,
            answer=answer,
            sources=sources,
            embedding=None,
            intent=intent_str
        )

        return {
            "answer": answer,
            "sources": sources,
            "type": "knowledge_qa",
            "cached": False
        }

    async def _handle_personal_query(
        self,
        query: str,
        state: DialogueState,
        user_info: Optional[Dict]
    ) -> Dict[str, Any]:
        """处理个人查询"""
        # 检查是否已绑定身份
        if not user_info or not user_info.get("is_bound"):
            return {
                "answer": "为了查询您的个人信息，请先绑定学工号。\n\n绑定步骤：\n1. 点击【个人中心】\n2. 选择【身份绑定】\n3. 输入学号和密码",
                "type": "auth_required"
            }

        # 检查缺失槽位
        missing = SlotFiller.check_missing_slots(
            IntentType.PERSONAL_QUERY,
            state.filled_slots
        )

        if missing:
            # 追问缺失信息
            if "semester" in missing:
                return {
                    "answer": "请问您要查询哪个学期的信息？（如：本学期、上学期、2024-2025-1）",
                    "type": "clarification",
                    "missing_slots": missing
                }
            elif "query_type" in missing:
                return {
                    "answer": "请问您想查询什么？（课表、成绩、考试安排、学分）",
                    "type": "clarification",
                    "missing_slots": missing
                }

        # 参数齐全，执行查询（模拟）
        query_type = state.filled_slots.get("query_type")
        semester = state.filled_slots.get("semester", "本学期")

        # 这里应该调用教务系统API
        # 现在返回模拟数据
        mock_data = self._generate_mock_personal_data(query_type, semester, user_info)

        return {
            "answer": mock_data,
            "type": "personal_query",
            "data": {
                "query_type": query_type,
                "semester": semester
            }
        }

    async def _handle_affair_guide(
        self,
        query: str,
        state: DialogueState
    ) -> Dict[str, Any]:
        """处理事务办理向导"""
        # 检索办事指南
        retrieval_results = await retriever.retrieve(
            query=f"{query} 办理流程",
            use_keyword=True
        )

        if retrieval_results:
            context = self._build_context(retrieval_results)
            answer = await self.llm.generate_guide(
                query=query,
                context=context,
                stage=state.filled_slots.get("stage", "overview")
            )

            return {
                "answer": answer,
                "sources": [
                    {"title": r.metadata.get("title", "")}
                    for r in retrieval_results[:2]
                ],
                "type": "affair_guide"
            }

        return {
            "answer": f"关于{query}的办理流程，我暂时没有找到详细信息。建议您：\n1. 咨询相关部门\n2. 查看学校官网",
            "type": "fallback"
        }

    async def _handle_chitchat(
        self,
        query: str,
        state: DialogueState
    ) -> Dict[str, Any]:
        """处理闲聊"""
        greetings = {
            "你好": "你好！我是校园百事通小百，有什么可以帮你的吗？😊",
            "谢谢": "不客气！有问题随时找我~",
            "再见": "再见！祝你学习顺利！",
            "在吗": "在的！有什么可以帮你的吗？"
        }

        for keyword, response in greetings.items():
            if keyword in query:
                return {
                    "answer": response,
                    "type": "chitchat"
                }

        return {
            "answer": "你好！我是校园百事通，专注于解答校园相关问题。有什么可以帮你的吗？",
            "type": "chitchat"
        }

    async def _handle_unknown(
        self,
        query: str,
        state: DialogueState
    ) -> Dict[str, Any]:
        """处理未知意图"""
        # 尝试用RAG检索，看是否能找到相关信息
        retrieval_results = await retriever.retrieve(query)

        if retrieval_results and retrieval_results[0].score > 0.8:
            # 检索结果较好，按知识问答处理
            return await self._handle_knowledge_qa(query, state)

        return {
            "answer": self._generate_fallback_response(query),
            "type": "unknown"
        }

    def _build_context(self, retrieval_results: List[Any]) -> str:
        """构建检索上下文"""
        contexts = []
        for i, result in enumerate(retrieval_results[:3], 1):
            title = result.metadata.get("title", "")
            content = result.content
            contexts.append(f"[文档{i}] {title}\n{content}\n")
        return "\n".join(contexts)

    def _generate_fallback_response(self, query: str) -> str:
        """生成兜底回复"""
        return f"""抱歉，关于"{query[:30]}..."这个问题，我暂时没有找到确切答案。

建议您通过以下方式获取帮助：
1. 咨询您的辅导员
2. 拨打教务处电话：(0731) 84618042
3. 前往行政楼教务处现场咨询

或者您可以换个方式提问，我会尽力帮您解答！"""

    def _generate_mock_personal_data(
        self,
        query_type: str,
        semester: str,
        user_info: Dict
    ) -> str:
        """生成模拟个人数据（实际项目中应调用真实API）"""
        if query_type == "schedule":
            return f"""您{semester}的课表如下：

**周一**：
- 08:00-09:40 高等数学 @ 教学楼A301
- 14:00-15:40 大学英语 @ 教学楼B205

**周二**：
- 10:00-11:40 程序设计基础 @ 实验楼C402

**周三**：
- 08:00-09:40 线性代数 @ 教学楼A302

（以上为模拟数据，实际项目需对接教务系统API）"""

        elif query_type == "grades":
            return f"""您{semester}的成绩如下：

| 课程 | 学分 | 成绩 | 绩点 |
|------|------|------|------|
| 高等数学 | 4.0 | 85 | 3.5 |
| 大学英语 | 3.0 | 90 | 4.0 |
| 程序设计 | 3.5 | 78 | 3.0 |

**学期GPA**: 3.5
**总学分**: 10.5

（以上为模拟数据）"""

        return f"已收到您的{query_type}查询请求（模拟数据）"


# 全局工作流实例
workflow = AgentWorkflow()
