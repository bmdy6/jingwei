"""项目全局路径常量，统一管理所有目录路径解析，消除各处重复的 parents[2] 拼接。"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_MEMORY_DIR = Path(os.getenv("MYAGENT_AGENT_MEMORY_DIR", str(PROJECT_ROOT / "agent_memory"))).expanduser()
SKILLS_DIR = AGENT_MEMORY_DIR / "skills"
EXPERIENCES_DIR = AGENT_MEMORY_DIR / "experiences"
CONTEXT_DIR = AGENT_MEMORY_DIR / "context"
SELF_EVOLUTION_DIR = SKILLS_DIR / "自学习技能"


def runtime_path(variable: str, default: str) -> Path:
    """Resolve writable application state under an explicit directory or the home folder."""
    return Path(os.getenv(variable) or str(Path.home() / ".xl-agent" / default)).expanduser()
