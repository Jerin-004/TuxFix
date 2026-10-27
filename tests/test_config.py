"""Tests for configuration module."""
from __future__ import annotations

import os
import pytest

from tuxfix.config import TuxFixConfig, get_config, load_config


class TestTuxFixConfig:
    def test_defaults(self):
        config = TuxFixConfig()
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.demo_mode is False
        assert config.ollama_timeout == 120

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://myserver:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "llama3")
        monkeypatch.setenv("TUXFIX_DEMO_MODE", "true")
        config = TuxFixConfig()
        assert config.ollama_base_url == "http://myserver:11434"
        assert config.ollama_model == "llama3"
        assert config.demo_mode is True

    def test_api_url_generation(self):
        config = TuxFixConfig(ollama_base_url="http://localhost:11434")
        assert config.ollama_api_generate == "http://localhost:11434/api/generate"
        assert config.ollama_api_tags == "http://localhost:11434/api/tags"

    def test_trailing_slash_stripped(self):
        config = TuxFixConfig(ollama_base_url="http://localhost:11434/")
        assert not config.ollama_api_generate.startswith("http://localhost:11434//")

    def test_as_display_dict_no_secrets(self):
        config = TuxFixConfig()
        d = config.as_display_dict()
        assert "ollama_base_url" in d
        # Should not expose anything named token or password
        for k in d:
            assert "password" not in k.lower()
            assert "token" not in k.lower()
            assert "secret" not in k.lower()

    def test_demo_mode_false_by_default(self, monkeypatch):
        monkeypatch.delenv("TUXFIX_DEMO_MODE", raising=False)
        config = TuxFixConfig()
        assert config.demo_mode is False


class TestLoadConfig:
    def test_load_config_with_overrides(self):
        config = load_config(ollama_model="custom-model", demo_mode=True)
        assert config.ollama_model == "custom-model"
        assert config.demo_mode is True

    def test_get_config_returns_instance(self):
        config = get_config()
        assert isinstance(config, TuxFixConfig)
