"""项目全局路径常量与可覆盖的运行时数据目录。"""
import sys
from pathlib import Path
from .environment import env_get

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_MEMORY_DIR = Path(env_get("JINGWEI_AGENT_MEMORY_DIR") or str(PROJECT_ROOT / "agent_memory")).expanduser()
SKILLS_DIR = AGENT_MEMORY_DIR / "skills"
EXPERIENCES_DIR = AGENT_MEMORY_DIR / "experiences"
CONTEXT_DIR = AGENT_MEMORY_DIR / "context"
SELF_EVOLUTION_DIR = SKILLS_DIR / "自学习技能"


def data_dir() -> Path:
    return Path(env_get("JINGWEI_DATA_DIR") or str(Path.home() / ".jingwei")).expanduser()


def runtime_path(variable: str, default: str) -> Path:
    """Explicit per-directory overrides take precedence over the data root."""
    return Path(env_get(variable) or str(data_dir() / default)).expanduser()


def warn_legacy_data_dir():
    """Notify before creating state, without moving, deleting or creating any data."""
    old = Path.home() / ".xl-agent"
    new = Path.home() / ".jingwei"
    if old.is_dir() and not new.exists():
        print(f"[Jingwei] 检测到旧数据目录 {old}，默认数据目录已改为 {new}。"
              f"不会自动移动或删除数据；继续使用旧数据可设置 JINGWEI_DATA_DIR={old}，"
              "或自行备份后迁移。", file=sys.stderr)
