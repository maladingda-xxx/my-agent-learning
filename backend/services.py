import os
from datetime import datetime
from  contextlib import contextmanager
import time
from .settings import settings
@contextmanager
def log_file():
    """上下文管理器：安全呢打开日志文件，自动关闭"""
    os.makedirs(os.path.dirname(settings.log_path),exist_ok=True)
    f = open(settings.log_path,"a",encoding="utf-8")
    try:
        yield f
    finally:
        f.close()


def log_chat(message:str,reply:str):
    """使用上下文管理器写日志"""
    now = datetime.now().isoformat()
    with log_file() as f:
       
        f.write(f"[{now}] User: {message}\n")
        f.write(f"[{now}] AI: {reply}\n")
        f.write("-"*50+"\n")
def read_recent_logs(n:int = 10):
    """读取最近n条对话记录"""
    if not os.path.exists(settings.log_path):
        return []
    with open(settings.log_path,"r",encoding="utf-8") as f:
        lines = f.readlines()

    user_lines = [line for line in lines if line.startswith("[") and "User:" in line]
    return user_lines[-n:]