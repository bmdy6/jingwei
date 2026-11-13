"""Rename contracts, exercised with clean processes and isolated user state."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_python(code, tmp_path, values=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("JINGWEI_", "MYAGENT_", "XL_"))}
    env.update(HOME=str(tmp_path), PYTHONPATH=str(ROOT))
    env.update(values or {})
    return subprocess.run([sys.executable, "-c", code], env=env, cwd=tmp_path,
                          text=True, capture_output=True, check=True)


@pytest.mark.parametrize("process,dotenv,yaml_values,expected", [
    ({"JINGWEI_MODEL": "new", "MYAGENT_MODEL": "old", "XL_MODEL": "xl"}, {}, {}, "new"),
    ({"MYAGENT_MODEL": "old", "XL_MODEL": "xl"}, {}, {}, "old"),
    ({"XL_MODEL": "xl"}, {}, {}, "xl"),
    ({"MYAGENT_MODEL": "process"}, {"JINGWEI_MODEL": "dotenv"}, {"JINGWEI_MODEL": "yaml"}, "process"),
    ({"JINGWEI_MODEL": "process"}, {"MYAGENT_MODEL": "dotenv"}, {}, "process"),
    ({}, {"MYAGENT_MODEL": "dotenv"}, {"JINGWEI_MODEL": "yaml"}, "dotenv"),
    ({}, {"JINGWEI_MODEL": "new", "MYAGENT_MODEL": "old"}, {}, "new"),
    ({}, {}, {"MYAGENT_MODEL": "old"}, "old"),
    ({}, {}, {"JINGWEI_MODEL": "new", "MYAGENT_MODEL": "old"}, "new"),
    ({"JINGWEI_MODEL": "", "MYAGENT_MODEL": "old"}, {}, {}, ""),
    ({"MODEL_CHOICE": "process"}, {"MODEL_CHOICE": "dotenv", "JINGWEI_MODEL": "${MODEL_CHOICE}"}, {}, "process"),
])
def test_config_source_and_alias_precedence(tmp_path, process, dotenv, yaml_values, expected):
    import yaml
    (tmp_path / ".env").write_text("".join(f"{k}={v}\n" for k, v in dotenv.items()))
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(yaml_values))
    code = """
import json, os
from pathlib import Path
import agent.core.config as config
# Module startup must use the same temporary sources as explicit reload.
settings = config.Settings(root=Path.cwd())
print(json.dumps([settings.get('JINGWEI_MODEL'), settings.get('MYAGENT_MODEL'), settings.get('XL_MODEL')]))
"""
    # Import core eagerly creates the singleton; use a copied package to isolate its YAML/.env too.
    import shutil
    shutil.copytree(ROOT / "agent", tmp_path / "agent", ignore=shutil.ignore_patterns("__pycache__"))
    result = run_python(code, tmp_path, process)
    assert json.loads(result.stdout.splitlines()[-1]) == [expected] * 3


@pytest.mark.parametrize("new_exists,old_exists,warning", [
    (False, True, True), (True, True, False), (False, False, False), (True, False, False),
])
def test_legacy_data_warning_is_non_mutating(tmp_path, new_exists, old_exists, warning):
    new = tmp_path / ".jingwei"
    old = tmp_path / ".xl-agent"
    if new_exists:
        new.mkdir()
    if old_exists:
        old.mkdir()
        (old / "sentinel").write_text("keep me")
    result = run_python("from agent.core.paths import warn_legacy_data_dir; warn_legacy_data_dir()", tmp_path)
    assert ("检测到旧数据目录" in result.stderr) is warning
    assert new.exists() is new_exists
    assert old.exists() is old_exists
    if old_exists:
        assert (old / "sentinel").read_text() == "keep me"
        assert "JINGWEI_DATA_DIR" in result.stderr if warning else True


@pytest.mark.parametrize("values,relative", [
    ({}, ".jingwei/sessions"),
    ({"JINGWEI_DATA_DIR": "~/custom"}, "custom/sessions"),
    ({"MYAGENT_DATA_DIR": "~/legacy-root"}, "legacy-root/sessions"),
    ({"JINGWEI_DATA_DIR": "~/custom", "MYAGENT_SESSION_DIR": "~/old-sessions"}, "old-sessions"),
    ({"JINGWEI_SESSION_DIR": "~/new-sessions", "MYAGENT_SESSION_DIR": "~/old-sessions"}, "new-sessions"),
])
def test_session_path_overrides(tmp_path, values, relative):
    result = run_python("""
from agent.session.handler import SessionHandler
print(SessionHandler('rename').storage_dir)
""", tmp_path, values)
    assert Path(result.stdout.strip()) == tmp_path / relative


def test_memory_and_notes_follow_data_root(tmp_path):
    result = run_python("""
from agent.memory.manager import MemoryManager
from agent.memory.store import get_kb_dir
print(MemoryManager().base_dir)
print(get_kb_dir())
""", tmp_path, {"JINGWEI_DATA_DIR": "~/custom"})
    assert result.stdout.splitlines()[-2:] == [str(tmp_path / "custom/memory"), str(tmp_path / "custom/notes")]


@pytest.mark.parametrize("launcher", ["jingwei", "xl"])
def test_cli_help_offline(tmp_path, launcher):
    env = dict(os.environ, HOME=str(tmp_path), PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    result = subprocess.run([str(ROOT / launcher), "--help"], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "精卫 / Jingwei" in result.stdout
    assert "./jingwei" in result.stdout
    assert not (tmp_path / ".jingwei").exists()


@pytest.mark.parametrize("launcher", ["jingwei", "xl"])
def test_launcher_preserves_arguments_and_exit_code(tmp_path, launcher):
    import shutil
    for name in ("jingwei", "xl"):
        shutil.copy2(ROOT / name, tmp_path / name)
    fake_bin = tmp_path / ".venv/bin"
    fake_bin.mkdir(parents=True)
    fake = fake_bin / "python"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\nexit 7\n')
    fake.chmod(0o755)
    result = subprocess.run([str(tmp_path / launcher), "a b", "中文", "--literal"], cwd="/", text=True, capture_output=True)
    assert result.returncode == 7
    assert result.stdout.splitlines() == [str(tmp_path / "main.py"), "a b", "中文", "--literal"]


def test_startup_warns_before_state_creation_and_labels_logs(tmp_path):
    old = tmp_path / ".xl-agent"
    old.mkdir()
    (old / "sentinel").write_text("unchanged")
    result = run_python("""
import logging
from agent.core.bootstrap import setup_system
setup_system()
logging.getLogger('rename').info('startup check')
logging.shutdown()
""", tmp_path)
    assert "检测到旧数据目录" in result.stderr
    assert not (tmp_path / ".jingwei").exists()
    assert (old / "sentinel").read_text() == "unchanged"
    assert "[Jingwei]" in (tmp_path / "logs/system.log").read_text()


def test_explicit_memory_path_beats_root_and_legacy_name(tmp_path):
    result = run_python("""
from agent.memory.manager import MemoryManager
print(MemoryManager().base_dir)
""", tmp_path, {"JINGWEI_DATA_DIR": "~/root", "JINGWEI_MEMORY_DIR": "~/new-memory",
                 "MYAGENT_MEMORY_DIR": "~/old-memory"})
    assert result.stdout.splitlines()[-1] == str(tmp_path / "new-memory")
