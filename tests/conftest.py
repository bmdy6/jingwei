"""Keep offline tests away from real credentials, services and user state."""
import copy
import os
import tempfile

# Apply before collection-time imports resolve home-based paths.
_test_home = tempfile.TemporaryDirectory(prefix="jingwei-test-home-")
os.environ["HOME"] = _test_home.name
import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    from agent.core.config import settings
    from agent.core import paths

    for key in list(__import__("os").environ):
        if key.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_PASS")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    original = copy.deepcopy(settings._data)
    settings._data["memory"] = {
        "base_dir": str(tmp_path / "memory"),
        "backup_dir": str(tmp_path / "backup"),
        "auto_backup_to_project": False,
        "multi_instance_isolation": False,
    }
    settings._data["knowledge_base"] = {"notes_paths": [], "kb_dir": str(tmp_path / "notes")}
    monkeypatch.setenv("JINGWEI_KB_DIR", str(tmp_path / "notes"))
    monkeypatch.setenv("EMBEDDING_MODE", "local")
    monkeypatch.setattr("agent.evolution.traces.TRACES_DIR", tmp_path / "traces")
    for name, suffix in [("AGENT_MEMORY_DIR", ""), ("SKILLS_DIR", "skills"),
                         ("EXPERIENCES_DIR", "experiences"), ("CONTEXT_DIR", "context"),
                         ("SELF_EVOLUTION_DIR", "skills/自学习技能")]:
        target = tmp_path / "agent_memory" / suffix
        target.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths, name, target)
    def deny_network(sock, address):
        raise RuntimeError(f"Offline test attempted a network connection: {address}")
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    try:
        yield
    finally:
        settings._data.clear()
        settings._data.update(original)
