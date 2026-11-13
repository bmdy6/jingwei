#!/usr/bin/env python3
"""Jingwei — 通用 AI Agent CLI 启动器

用法：
    python main.py                          # 交互模式
    python main.py "请帮我读一下 README.md"   # 单次模式
"""

import sys

# Handle help before importing the runtime: no models, credentials or state needed.
if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help"}:
    print("""精卫 / Jingwei — 通用 AI Agent
用法：./jingwei [问题 | 模式]
  不带参数             交互模式
  "问题"               单次对话
  --gateway            QQ 网关
  --auto-learn         自主学习
  --cleanup            知识库清理
  --dashboard          实验仪表盘
  --dashboard-learn    仪表盘自主学习
  --douyin             独立网关状态提示
  -h, --help           显示帮助
数据：默认 ~/.jingwei；JINGWEI_DATA_DIR 可覆盖。
./xl 为兼容旧名，后续移除。""")
    raise SystemExit(0)

from agent.core.bootstrap import setup_system
from agent.runner import (
    run_interactive,
    run_single,
    run_auto_learn,
    run_dashboard,
    run_dashboard_learn,
    run_gateway,
    run_douyin_gateway
)

def _run_safe(coro):
    import asyncio
    try:
        asyncio.run(coro)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    setup_system()
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--gateway":
            _run_safe(run_gateway())
        elif arg == "--douyin":
            _run_safe(run_douyin_gateway())
        elif arg == "--auto-learn":
            _run_safe(run_auto_learn())
        elif arg == "--cleanup":
            from agent.core.cleanup import run_cleanup
            from agent.core.bootstrap import build_agent
            _run_safe(run_cleanup(build_agent()))
        elif arg == "--dashboard":
            _run_safe(run_dashboard())
        elif arg == "--dashboard-learn":
            _run_safe(run_dashboard_learn())
        else:
            _run_safe(run_single(" ".join(sys.argv[1:])))
    else:
        _run_safe(run_interactive())
