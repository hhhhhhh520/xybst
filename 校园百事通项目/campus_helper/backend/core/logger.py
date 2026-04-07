"""
日志配置
"""
import sys
from pathlib import Path
from loguru import logger as _logger

from core.config import settings

# 确保日志目录存在
log_dir = Path(settings.LOG_FILE).parent
log_dir.mkdir(parents=True, exist_ok=True)

# 配置日志
_logger.remove()

# 控制台输出（简化格式，避免编码问题）
_logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}")

# 文件输出
_logger.add(
    settings.LOG_FILE,
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="10 MB",
    retention="30 days",
    encoding="utf-8"
)

logger = _logger
