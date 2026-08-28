"""模型供应商管理模块 —— 支持多供应商配置、持久化、CRUD"""

import json
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from settings import DATA_DIR

PROVIDERS_FILE = DATA_DIR / "providers.json"


class ProviderConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str  # 显示名称，如 "DeepSeek", "OpenAI", "Claude"
    api_base: str  # API base URL
    api_key: str  # API Key
    models: list[str] = []  # 可用模型列表
    enabled: bool = True


class ProviderStore:
    """JSON 文件持久化的供应商管理"""

    def __init__(self):
        self._providers: list[ProviderConfig] = []
        self._load()

    def _load(self):
        if PROVIDERS_FILE.exists():
            try:
                data = json.loads(PROVIDERS_FILE.read_text(encoding="utf-8"))
                self._providers = [ProviderConfig(**p) for p in data]
            except (json.JSONDecodeError, Exception):
                self._providers = []
        else:
            # 初始化默认的 DeepSeek 供应商（从 settings 获取）
            self._init_default()

    def _init_default(self):
        from settings import settings
        default = ProviderConfig(
            id="default",
            name="DeepSeek",
            api_base=settings.deepseek_api_base,
            api_key=settings.deepseek_api_key,
            models=["deepseek-chat", "deepseek-reasoner"],
        )
        self._providers = [default]
        self._save()

    def _save(self):
        PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [p.model_dump() for p in self._providers]
        PROVIDERS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_all(self) -> list[ProviderConfig]:
        return self._providers

    def get(self, provider_id: str) -> ProviderConfig | None:
        for p in self._providers:
            if p.id == provider_id:
                return p
        return None

    def add(self, config: ProviderConfig) -> ProviderConfig:
        self._providers.append(config)
        self._save()
        return config

    def update(self, provider_id: str, data: dict) -> ProviderConfig | None:
        for i, p in enumerate(self._providers):
            if p.id == provider_id:
                updated = p.model_copy(update=data)
                self._providers[i] = updated
                self._save()
                return updated
        return None

    def delete(self, provider_id: str) -> bool:
        before = len(self._providers)
        self._providers = [p for p in self._providers if p.id != provider_id]
        if len(self._providers) < before:
            self._save()
            return True
        return False

    def find_model(self, model_name: str) -> tuple[ProviderConfig, str] | None:
        """根据模型名找到对应的供应商配置"""
        for p in self._providers:
            if not p.enabled:
                continue
            if model_name in p.models:
                return p, model_name
        # fallback：返回第一个 enabled 的供应商的第一个模型
        for p in self._providers:
            if p.enabled and p.models:
                return p, p.models[0]
        return None


# 单例
provider_store = ProviderStore()
