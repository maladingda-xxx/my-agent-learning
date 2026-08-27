"""
LangChain Agent 服务
"""
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools import calculator, get_current_time, retrieve_knowledge
from dependencies import get_settings

# 全局 AgentExecutor 实例（懒加载）
_agent_executor = None

def get_agent_executor():
    """创建或返回已初始化的 AgentExecutor"""
    global _agent_executor
    if _agent_executor is not None:
        return _agent_executor

    cfg = get_settings()
    # 1. 创建 LLM（LangChain 的 ChatOpenAI 兼容 DeepSeek）
    llm = ChatOpenAI(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_api_base,
        model=cfg.model_name,
        temperature=0.3,
    )

    # 2. 工具列表
    tools = [calculator, get_current_time, retrieve_knowledge]

    # 3. Prompt 模板（使用 system 和 human 消息）
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个智能知识库助手。你可以使用工具来回答问题。"
                   "优先使用知识库检索工具获取资料，如果问题需要计算或查看时间，再使用对应工具。"
                   "回答时请引用来源（如“根据[1]”）。"),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # 4. 创建 Agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 5. 执行器
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=5)
    _agent_executor = executor
    return executor

async def ask_agent(question: str, session_id: str = "default") -> str:
    """调用 Agent 处理问题"""
    executor = get_agent_executor()
    # 简单起见，不维护会话历史；未来可接入 session_store
    result = await executor.ainvoke({"input": question})
    return result["output"]