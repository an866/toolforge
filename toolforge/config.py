"""ToolForge 配置管理。"""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_LLM_")
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-v4-pro"
    base_url: str = "https://api.deepseek.com/v1"
    max_retries: int = 3
    timeout: int = 60


class SandboxConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_SANDBOX_")
    memory_limit_mb: int = 256
    cpu_limit: float = 1.0
    timeout_seconds: int = 30
    pids_limit: int = 50
    base_image: str = "python:3.12-slim"


class SmithConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_SMITH_")
    template_match_threshold: float = 0.7
    max_fix_attempts: int = 2


class RegistryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_REGISTRY_")
    db_path: str = "./data/toolforge.db"
    vector_path: str = "./data/chromadb"
    tools_path: str = "./tool_registry"


class SecurityConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_SECURITY_")
    human_approval_mode: bool = False
    max_inventions_per_task: int = 5
    rate_limit_per_tool: int = 50


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    smith: SmithConfig = Field(default_factory=SmithConfig)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config(config_or_path: Config | str | Path) -> Config:
    global _config
    if isinstance(config_or_path, Config):
        _config = config_or_path
    else:
        _config = Config.from_yaml(config_or_path)
    return _config
