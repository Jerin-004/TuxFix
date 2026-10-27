"""
TuxFix configuration — reads from environment variables / .env file.
Never exposes secrets or credential values through the public API.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; fall back to raw env vars

logger = logging.getLogger(__name__)


@dataclass
class TuxFixConfig:
    """Central configuration object for TuxFix."""

    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "codegemma:2b")
    )
    ollama_timeout: int = field(
        default_factory=lambda: int(os.getenv("OLLAMA_TIMEOUT", "120"))
    )
    demo_mode: bool = field(
        default_factory=lambda: os.getenv("TUXFIX_DEMO_MODE", "false").lower() == "true"
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )

    def __post_init__(self) -> None:
        logging.basicConfig(level=getattr(logging, self.log_level, logging.INFO))

    @property
    def ollama_api_generate(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}/api/generate"

    @property
    def ollama_api_tags(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}/api/tags"

    def as_display_dict(self) -> dict:
        """Safe dict for display — never exposes credentials."""
        return {
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "ollama_timeout": self.ollama_timeout,
            "demo_mode": self.demo_mode,
            "log_level": self.log_level,
        }


# Singleton — re-instantiate after calling load_config()
_config: Optional[TuxFixConfig] = None


def get_config() -> TuxFixConfig:
    global _config
    if _config is None:
        _config = TuxFixConfig()
    return _config


def load_config(**overrides) -> TuxFixConfig:
    """Create a fresh config, applying keyword overrides."""
    global _config
    _config = TuxFixConfig()
    for k, v in overrides.items():
        if hasattr(_config, k):
            setattr(_config, k, v)
    return _config
