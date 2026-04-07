"""
核心配置模块
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用信息
    APP_NAME: str = "校园百事通"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/campus_helper.db"

    # 向量数据库
    CHROMA_PERSIST_DIR: str = "./data/knowledge_base"
    CHROMA_COLLECTION_NAME: str = "campus_knowledge"

    # AI模型配置
    LLM_PROVIDER: str = "zhipu"  # 默认使用智谱AI

    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Anthropic配置
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"

    # 本地模型配置
    LOCAL_MODEL_URL: str = "http://localhost:11434"
    LOCAL_MODEL_NAME: str = "qwen:7b"

    # 智谱AI配置
    ZHIPU_API_KEY: str = ""
    ZHIPU_MODEL: str = "glm-4-flash"

    # Embedding模型
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_CACHE_DIR: str = "./models/embedding"  # 模型本地缓存目录

    # RAG配置
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.0  # 设为0，让RRF融合结果都能通过
    RAG_CHUNK_SIZE: int = 400
    RAG_CHUNK_OVERLAP: int = 50

    # BM25配置
    BM25_K1: float = 1.5  # BM25参数k1
    BM25_B: float = 0.75  # BM25参数b

    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/campus_helper.log"

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置（单例）"""
    # 打印调试信息
    env_path = Path(".env")
    if env_path.exists():
        print(f"[配置] 找到.env文件: {env_path.absolute()}")
    return Settings()


settings = get_settings()
