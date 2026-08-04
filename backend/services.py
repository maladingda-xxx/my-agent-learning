import os
from datetime import datetime
LOG_DIR = os.path.join(os.path.dirname(__file__),"..","logs")

def ensure_log_dir():
    """确保日志目录存在，不存在则创建"""
    os.makedirs(LOG_DIR,exist_ok=True)
def log_chat(message:str,reply:str):
    """将聊天记录追加到日志文件"""
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR,"chat_history.txt")
    now = datetime.now().isoformat()

    with open(log_path,"a",encoding="utf-8") as f:
        f.write(f"[{now}] User: {message}\n")
        f.write(f"[{now}] AI: {reply}\n")
        f.write("-"*50+"\n")