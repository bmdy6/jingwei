import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from .environment import aliases, env_get, normalize

logger = logging.getLogger("agent.config")


class Settings:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        self._data = {}
        self.load()

    @staticmethod
    def _inject(values):
        for key, val in normalize(values).items():
            if val is not None and not isinstance(val, (dict, list)):
                os.environ.setdefault(key, str(val).lower() if isinstance(val, bool) else str(val))

    def load(self):
        """Process > .env > YAML; JINGWEI names win within each source."""
        try:
            # Normalize each layer before injecting the next. An old process key
            # must still beat a new .env/YAML key, including explicitly empty values.
            self._inject(dict(os.environ))
            # Keep round 1 interpolation semantics: process values win inside ${...}.
            load_dotenv(self.root / ".env", override=False)
            self._inject(dict(os.environ))
            yaml_path = self.root / "config" / "settings.yaml"
            if not yaml_path.exists():
                yaml_path = self.root / "config.yaml"
            if yaml_path.exists():
                import yaml
                parsed = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    self._data = normalize(parsed)
                    self._inject(self._data)
                logger.info(f"Successfully loaded config from {yaml_path}")
            else:
                logger.warning("Centralized config file settings.yaml not found, falling back to env.")
        except Exception as e:
            logger.error(f"Failed to load centralized YAML config: {e}")

    def __getattr__(self, name: str):
        return self.get(name, "")

    def get(self, name: str, default=None):
        value = env_get(name)
        if value is not None:
            return value
        return self._data.get(aliases(name)[0], default)

    def enabled(self, name: str) -> bool:
        return str(self.get(name, False)).strip().lower() in {"1", "true", "yes", "on"}

    def get_threshold(self, key: str, default):
        """从 thresholds 配置节读取阈值，缺失时返回 default 保证不崩溃。"""
        thresholds = self._data.get("thresholds", {})
        if isinstance(thresholds, dict):
            return thresholds.get(key, default)
        return default


settings = Settings()
