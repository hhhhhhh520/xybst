"""
核心配置模块 - 兼容层

此文件提供向后兼容，实际配置从 config 模块加载
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 从 config 模块导入
from config import settings, get_settings, Settings

# 为了向后兼容，创建一个兼容层类
class _SettingsCompat:
    """
    配置兼容层 - 提供与旧配置相同的属性访问方式
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    # 应用配置
    @property
    def APP_NAME(self) -> str:
        return self._settings.app.name

    @property
    def APP_VERSION(self) -> str:
        return self._settings.app.version

    @property
    def DEBUG(self) -> bool:
        return self._settings.app.debug

    @property
    def HOST(self) -> str:
        return self._settings.app.host

    @property
    def PORT(self) -> int:
        return self._settings.app.port

    # 数据库配置
    @property
    def DATABASE_URL(self) -> str:
        return self._settings.database.url

    # 向量数据库配置
    @property
    def CHROMA_PERSIST_DIR(self) -> str:
        return self._settings.vector_db.persist_dir

    @property
    def CHROMA_COLLECTION_NAME(self) -> str:
        return self._settings.vector_db.collection_name

    # LLM 配置
    @property
    def LLM_PROVIDER(self) -> str:
        return self._settings.llm.provider

    # OpenAI 配置
    @property
    def OPENAI_API_KEY(self) -> str:
        return self._settings.llm.providers.get("openai", ProviderConfig()).api_key

    @property
    def OPENAI_MODEL(self) -> str:
        return self._settings.llm.providers.get("openai", ProviderConfig()).model

    @property
    def OPENAI_BASE_URL(self) -> str:
        return self._settings.llm.providers.get("openai", ProviderConfig()).base_url

    # Anthropic 配置
    @property
    def ANTHROPIC_API_KEY(self) -> str:
        return self._settings.llm.providers.get("anthropic", ProviderConfig()).api_key

    @property
    def ANTHROPIC_MODEL(self) -> str:
        return self._settings.llm.providers.get("anthropic", ProviderConfig()).model

    # 智谱AI 配置
    @property
    def ZHIPU_API_KEY(self) -> str:
        return self._settings.llm.providers.get("zhipu", ProviderConfig()).api_key

    @property
    def ZHIPU_MODEL(self) -> str:
        return self._settings.llm.providers.get("zhipu", ProviderConfig()).model

    @property
    def ZHIPU_BASE_URL(self) -> str:
        return self._settings.llm.providers.get("zhipu", ProviderConfig()).base_url

    @property
    def ZHIPU_MAX_TOKENS(self) -> int:
        return self._settings.llm.providers.get("zhipu", ProviderConfig()).max_tokens

    @property
    def ZHIPU_TEMPERATURE(self) -> float:
        return self._settings.llm.providers.get("zhipu", ProviderConfig()).temperature

    @property
    def ZHIPU_TIMEOUT(self) -> float:
        return self._settings.llm.providers.get("zhipu", ProviderConfig()).timeout

    # 本地模型配置
    @property
    def LOCAL_MODEL_URL(self) -> str:
        return self._settings.llm.providers.get("local", ProviderConfig()).url

    @property
    def LOCAL_MODEL_NAME(self) -> str:
        return self._settings.llm.providers.get("local", ProviderConfig()).model

    # Embedding 配置
    @property
    def EMBEDDING_MODEL(self) -> str:
        return self._settings.embedding.model

    @property
    def EMBEDDING_DEVICE(self) -> str:
        return self._settings.embedding.device

    @property
    def EMBEDDING_CACHE_DIR(self) -> str:
        return self._settings.embedding.cache_dir

    # RAG 配置
    @property
    def RAG_TOP_K(self) -> int:
        return self._settings.rag.top_k

    @property
    def RAG_SIMILARITY_THRESHOLD(self) -> float:
        return self._settings.rag.similarity_threshold

    @property
    def RAG_CHUNK_SIZE(self) -> int:
        return self._settings.rag.chunk_size

    @property
    def RAG_CHUNK_OVERLAP(self) -> int:
        return self._settings.rag.chunk_overlap

    # BM25 配置
    @property
    def BM25_K1(self) -> float:
        return self._settings.bm25.k1

    @property
    def BM25_B(self) -> float:
        return self._settings.bm25.b

    # 安全配置
    @property
    def SECRET_KEY(self) -> str:
        return self._settings.security.secret_key

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self._settings.security.token_expire_minutes

    # 日志配置
    @property
    def LOG_LEVEL(self) -> str:
        return self._settings.logging.level

    @property
    def LOG_FILE(self) -> str:
        return self._settings.logging.file


# 导入 ProviderConfig 用于类型提示
from config import ProviderConfig

# 创建兼容层实例
settings_compat = _SettingsCompat(settings)

# 导出 settings 变量（向后兼容）
# 旧代码使用 settings.SETTING_NAME 的方式仍然有效
settings = settings_compat

# 同时导出新的配置对象
new_settings = get_settings()
