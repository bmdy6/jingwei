"""First-run contracts: environment precedence and opt-in channels."""
import os
import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.core.config import Settings, settings


def test_environment_wins_over_yaml(monkeypatch):
    monkeypatch.setenv("MYAGENT_API_KEY", "test-environment-key")
    monkeypatch.setenv("MYAGENT_MAX_TURNS", "2")
    config = Settings()
    assert os.environ["MYAGENT_API_KEY"] == "test-environment-key"
    assert config.get("MYAGENT_MAX_TURNS") == "2"


def test_defaults_are_portable():
    import yaml
    cfg = yaml.safe_load((Path(__file__).parents[1] / "config/settings.yaml").read_text())
    assert cfg["QQ_ENABLED"] is False
    assert cfg["QQ_ADMIN_ID"] == ""
    assert cfg["MY_AGENT_WHITE_LIST"] == ""
    assert cfg["QQ_WHITE_GROUPS"] == ""
    assert cfg["memory"]["auto_backup_to_project"] is False
    assert cfg["knowledge_base"]["notes_paths"] == []


@pytest.mark.asyncio
async def test_disabled_gateway_never_connects(monkeypatch):
    from agent.net_gateway.bot import QQGateway
    monkeypatch.setenv("QQ_ENABLED", "false")
    gateway = QQGateway(lambda _: None)
    with patch.object(gateway, "_start_brain_server") as start:
        with pytest.raises(RuntimeError, match="QQ_ENABLED"):
            await asyncio.wait_for(gateway.run(), timeout=0.1)
        start.assert_not_called()


@pytest.mark.asyncio
async def test_gateway_requires_admin_id(monkeypatch):
    from agent.net_gateway.bot import QQGateway
    monkeypatch.setenv("QQ_ENABLED", "true")
    monkeypatch.setenv("QQ_ADMIN_ID", "")
    gateway = QQGateway(lambda _: None)
    with pytest.raises(RuntimeError, match="QQ_ADMIN_ID"):
        await asyncio.wait_for(gateway.run(), timeout=0.1)


def test_cli_runner_imports_without_optional_services():
    import agent.runner
    assert callable(agent.runner.run_single)


def test_default_registry_has_no_qq_tools(monkeypatch):
    from agent.core.bootstrap import build_agent
    from agent.tools.registry import registry
    monkeypatch.setattr(registry, "_tools", {})
    monkeypatch.setattr(registry, "_cached_definitions", None)
    monkeypatch.setenv("QQ_ENABLED", "false")
    agent = build_agent()
    assert not {"get_qq_status", "send_qq_message", "send_image_to_qq"} & set(agent.registry.list_names())
