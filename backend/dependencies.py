from .settings import settings
def get_settings():
    """依赖注入：提供全局配置"""
    return settings