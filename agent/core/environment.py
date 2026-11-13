"""Environment aliases shared by configuration loading and runtime consumers."""
import os

PREFIXES = ("JINGWEI_", "MYAGENT_", "XL_")


def aliases(name: str) -> tuple[str, ...]:
    for prefix in PREFIXES:
        if name.startswith(prefix):
            suffix = name[len(prefix):]
            return tuple(p + suffix for p in PREFIXES)
    return (name,)


def env_get(name: str, default=None):
    """New names win within a source; Settings preserves precedence across sources."""
    for candidate in aliases(name):
        if candidate in os.environ:
            return os.environ[candidate]
    return default


def normalize(values: dict) -> dict:
    """Resolve aliases inside one source without letting lower sources mask old keys."""
    result = {}
    for key, value in values.items():
        names = aliases(str(key))
        result[names[0]] = next(values[n] for n in names if n in values)
    return result
