from datetime import datetime

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """获取当前系统时间，格式为 YYYY-MM-DD HH:MM:SS。当用户询问时间相关问题时使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS = [get_current_time]
