from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    deepseek_api_key:str
    deepseek_api_base:str = "https://api.deepseek.com"
    model_name:str = "deepseek-v4-flash"
    temperature:float = 0.3
    max_tokens:int = 1024
    log_path:str = "logs/chat.txt"
    chat_history_max_retrieve:int = 10
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()