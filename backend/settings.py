from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent          # backend/
PROJECT_ROOT = BASE_DIR.parent                        # 项目根目录
DATA_DIR = BASE_DIR / "data"                          # backend/data/
LOG_DIR = BASE_DIR / "logs"                           # backend/logs/


class Settings(BaseSettings):
    deepseek_api_key:str
    deepseek_api_base:str = "https://api.deepseek.com"
    model_name:str = "deepseek-v4-flash"
    temperature:float = 0.3
    max_tokens:int = 1024
    log_path:str = "logs/chat.txt"
    chat_history_max_retrieve:int = 10

    @field_validator("log_path")
    @classmethod
    def _resolve_log_path(cls, v: str) -> str:
        """把相对日志路径解析为基于 backend/ 的绝对路径"""
        p = Path(v)
        if not p.is_absolute():
            p = BASE_DIR / p
        return str(p)

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"

settings = Settings()