"""
数据库模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ========== 用户相关模型 ==========

class UserBase(BaseModel):
    """用户基础模型"""
    user_id: str = Field(..., description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")


class UserInfo(UserBase):
    """用户信息模型"""
    is_bound: bool = Field(False, description="是否绑定学工号")
    student_id: Optional[str] = Field(None, description="学号")
    name: Optional[str] = Field(None, description="姓名")
    college: Optional[str] = Field(None, description="学院")
    major: Optional[str] = Field(None, description="专业")
    grade: Optional[str] = Field(None, description="年级")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserBindRequest(BaseModel):
    """用户绑定请求"""
    user_id: str = Field(..., description="用户ID")
    student_id: str = Field(..., description="学号")
    password: str = Field(..., description="密码")


class UserBindResponse(BaseModel):
    """用户绑定响应"""
    success: bool
    message: str
    user_info: Optional[UserInfo] = None


# ========== 对话相关模型 ==========

class Message(BaseModel):
    """消息模型"""
    role: str = Field(..., description="角色: user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now)
    sources: Optional[List[dict]] = Field(None, description="引用来源")


class ChatSession(BaseModel):
    """对话会话模型"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    messages: List[Message] = Field(default_factory=list)
    intent: Optional[str] = Field(None, description="当前意图")
    slots: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息")
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    user_info: Optional[UserInfo] = None


class ChatResponse(BaseModel):
    """对话响应"""
    answer: str = Field(..., description="回答内容")
    type: str = Field(..., description="响应类型")
    sources: Optional[List[dict]] = Field(None, description="引用来源")
    data: Optional[dict] = Field(None, description="附加数据")
    cached: Optional[bool] = Field(None, description="是否来自缓存")


# ========== 文档相关模型 ==========

class DocumentMetadata(BaseModel):
    """文档元数据模型"""
    doc_id: str = Field(..., description="文档ID")
    title: str = Field(..., description="文档标题")
    source: str = Field(..., description="来源部门")
    doc_type: str = Field(..., description="文档类型")
    file_path: Optional[str] = Field(None, description="文件路径")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DocumentUpload(BaseModel):
    """文档上传模型"""
    content: str = Field(..., description="文档内容")
    title: str = Field(..., description="文档标题")
    source: str = Field(..., description="来源部门")
    doc_type: str = Field(default="policy", description="文档类型")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    success: bool
    doc_id: Optional[str] = None
    message: str


class DocumentChunk(BaseModel):
    """文档分块模型"""
    chunk_id: str = Field(..., description="分块ID")
    doc_id: str = Field(..., description="所属文档ID")
    content: str = Field(..., description="分块内容")
    chunk_index: int = Field(..., description="分块序号")
    chunk_total: int = Field(..., description="总分块数")
    metadata: dict = Field(default_factory=dict)


# ========== 检索相关模型 ==========

class RetrievalResult(BaseModel):
    """检索结果模型"""
    content: str = Field(..., description="内容")
    metadata: dict = Field(..., description="元数据")
    score: float = Field(..., description="相似度分数")
    source: str = Field(..., description="来源类型")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="查询文本")
    top_k: int = Field(default=5, description="返回数量")
    filter: Optional[dict] = Field(None, description="过滤条件")


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: List[RetrievalResult]
    total: int


# ========== 反馈相关模型 ==========

class Feedback(BaseModel):
    """用户反馈模型"""
    feedback_id: str = Field(..., description="反馈ID")
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    message_index: int = Field(..., description="消息索引")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: Optional[str] = Field(None, description="评论")
    created_at: datetime = Field(default_factory=datetime.now)


class FeedbackRequest(BaseModel):
    """反馈请求"""
    session_id: str
    message_index: int
    rating: int
    comment: Optional[str] = None


# ========== 统计相关模型 ==========

class KnowledgeStats(BaseModel):
    """知识库统计"""
    total_documents: int
    total_chunks: int
    sources: dict
    doc_types: dict
    embedding_model: str


class UsageStats(BaseModel):
    """使用统计"""
    total_sessions: int
    total_messages: int
    avg_session_duration: float
    avg_messages_per_session: float
    top_intents: List[dict]
    daily_active_users: int


class SystemStatus(BaseModel):
    """系统状态"""
    status: str
    version: str
    uptime: float
    llm_provider: str
    embedding_model: str
