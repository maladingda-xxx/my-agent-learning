"""工具定义模块——Agent可以调用工具"""

import json 
import math

def calculate(expression:str) -> str:
    try:
        allowed_chars = "0123456789+-*/()."
        if not all(c in allowed_chars for c in expression):
            return "错误，表达式包含非法字符"
        result = eval(expression,{"__builtins__":{}},{"math":math})
        return f"计算结果:{result}"
    except Exception as e:
        return f"错误，计算失败-{e}"

def get_current_time() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

TOOL_DEFINTIONS = [
    {
        "type":"function",
        "function":{
            "name":"calculate",
            "description":"计算数学表达式，支持简单的四则运算",
            "parameters":{
                "type":"object",
                "properties":{
                    "expression":{
                        "type":"string",
                        "description":"数学表达式，例如'2+3*4'"
                    }
                },
                "required":["expression"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"get_current_time",
            "description":"获取当前系统时间",
            "parameters":{
                "type":"object",
                "properties":{}
            }
        }
    }
]

def execute_tool(name:str,argument:dict) -> str:
    if name == "calculate":
        return calculate(argument.get("expression",""))
    elif name == "get_current_time":
        return get_current_time()
    else:
        return f"错误:未知工具{name}"