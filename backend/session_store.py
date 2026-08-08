"""简单的对话储存——生产环境要替换为Redis或数据库"""

from collections import defaultdict

sessions = defaultdict(list)
MAX_HISTORY = 10

def get_history(session_id:str) -> list[dict]:
    return sessions.get(session_id,[])

def add_to_history(session_id:str,role:str,content:str):
    sessions[session_id].append({"role":role,"content":content})

    if len(sessions[session_id]) > MAX_HISTORY * 2:
        sessions[session_id] = sessions[session_id][-(MAX_HISTORY * 2):]

def clear_history(session_id:str):
    sessions.pop(session_id,None)