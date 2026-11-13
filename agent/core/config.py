import os
import logging
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger("agent.config")

class Settings:
    def __init__(self):
        self._data = {}
        self.load()

    def load(self):
        """自适应从 config/settings.yaml 加载配置并注入环境变量"""
        try:
            load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
            # 找到项目根目录下的 config/settings.yaml
            root = Path(__file__).resolve().parents[2]
            yaml_path = root / "config" / "settings.yaml"
            
            if not yaml_path.exists():
                yaml_path = root / "config.yaml"
            
            if yaml_path.exists():
                import yaml
                content = yaml_path.read_text(encoding="utf-8")
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    self._data = parsed
                    # 自动注入到 os.environ，实现 100 percent 向后兼容
                    for key, val in parsed.items():
                        if val is not None and not isinstance(val, (dict, list)):
                            os.environ.setdefault(str(key), str(val).lower() if isinstance(val, bool) else str(val))
                logger.info(f"Successfully loaded config from {yaml_path}")
            else:
                logger.warning("Centralized config file settings.yaml not found, falling back to env.")
        except Exception as e:
            logger.error(f"Failed to load centralized YAML config: {e}")

    def __getattr__(self, name: str):
        return self.get(name, "")

    def get(self, name: str, default=None):
        if name in os.environ:
            return os.environ[name]
        return self._data.get(name, default)

    def enabled(self, name: str) -> bool:
        return str(self.get(name, False)).strip().lower() in {"1", "true", "yes", "on"}

    def get_threshold(self, key: str, default):
        """从 thresholds 配置节读取阈值，缺失时返回 default 保证不崩溃。"""
        thresholds = self._data.get("thresholds", {})
        if isinstance(thresholds, dict):
            return thresholds.get(key, default)
        return default

# 单例模式暴露
settings = Settings()
