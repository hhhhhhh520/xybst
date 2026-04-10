"""
配置加载器 - 支持 YAML 分离方案
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典，override 中的值会覆盖 base 中的值

    Args:
        base: 基础配置
        override: 覆盖配置

    Returns:
        合并后的配置
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_yaml_config(config_dir: Path) -> Dict[str, Any]:
    """
    加载 YAML 配置文件

    加载顺序：
    1. settings.yaml - 公共配置
    2. settings.local.yaml - 本地私有配置（覆盖公共配置）

    Args:
        config_dir: 配置文件目录

    Returns:
        合并后的配置字典
    """
    # 加载公共配置
    settings_path = config_dir / "settings.yaml"
    if not settings_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {settings_path}")

    with open(settings_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 加载本地配置（如果存在）
    local_path = config_dir / "settings.local.yaml"
    if local_path.exists():
        with open(local_path, "r", encoding="utf-8") as f:
            local_config = yaml.safe_load(f)
            if local_config:
                config = deep_merge(config, local_config)

    return config


@dataclass
class ProviderConfig:
    """LLM 提供商配置"""
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    url: str = ""
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: float = 120.0


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "zhipu"
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    def get_current_provider(self) -> ProviderConfig:
        """获取当前提供商的配置"""
        return self.providers.get(self.provider, ProviderConfig())


@dataclass
class EmbeddingConfig:
    """Embedding 配置"""
    model: str = "BAAI/bge-large-zh-v1.5"
    device: str = "cpu"
    cache_dir: str = "./models/embedding"


@dataclass
class RAGConfig:
    """RAG 配置"""
    top_k: int = 5
    similarity_threshold: float = 0.0
    chunk_size: int = 400
    chunk_overlap: int = 50


@dataclass
class BM25Config:
    """BM25 配置"""
    k1: float = 1.5
    b: float = 0.75


@dataclass
class VectorDBConfig:
    """向量数据库配置"""
    persist_dir: str = "./data/knowledge_base"
    collection_name: str = "campus_knowledge"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = "sqlite:///./data/campus_helper.db"


@dataclass
class AppConfig:
    """应用配置"""
    name: str = "校园百事通"
    version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = ""
    token_expire_minutes: int = 60


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "./logs/campus_helper.log"


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    max_size: int = 1000
    ttl_seconds: int = 3600
    similarity_threshold: float = 0.95
    stats_enabled: bool = True


@dataclass
class Settings:
    """应用配置总类"""
    app: AppConfig = field(default_factory=AppConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    bm25: BM25Config = field(default_factory=BM25Config)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """从字典创建配置对象"""
        settings = cls()

        if "app" in data:
            settings.app = AppConfig(**data["app"])
        if "database" in data:
            settings.database = DatabaseConfig(**data["database"])
        if "vector_db" in data:
            settings.vector_db = VectorDBConfig(**data["vector_db"])
        if "embedding" in data:
            settings.embedding = EmbeddingConfig(**data["embedding"])
        if "rag" in data:
            settings.rag = RAGConfig(**data["rag"])
        if "bm25" in data:
            settings.bm25 = BM25Config(**data["bm25"])
        if "security" in data:
            settings.security = SecurityConfig(**data["security"])
        if "logging" in data:
            settings.logging = LoggingConfig(**data["logging"])
        if "cache" in data:
            settings.cache = CacheConfig(**data["cache"])

        # 处理 LLM 配置（嵌套结构）
        if "llm" in data:
            llm_data = data["llm"]
            providers = {}
            if "providers" in llm_data:
                for name, provider_data in llm_data["providers"].items():
                    providers[name] = ProviderConfig(**provider_data)
            settings.llm = LLMConfig(
                provider=llm_data.get("provider", "zhipu"),
                providers=providers
            )

        return settings


def get_settings() -> Settings:
    """
    获取配置（单例模式）

    Returns:
        Settings 配置对象
    """
    global _settings

    if _settings is None:
        # 确定配置文件目录
        config_dir = Path(__file__).parent

        # 加载配置
        config_data = load_yaml_config(config_dir)

        # 创建配置对象
        _settings = Settings.from_dict(config_data)

    return _settings


# 全局配置对象
_settings: Optional[Settings] = None

# 初始化配置
settings = get_settings()
