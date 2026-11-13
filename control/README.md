# 可选进程控制脚本

`control/` 保留早期的 macOS / Docker 启停脚本，未作为本轮的启动方式验收。单次 CLI 的使用方式见根目录 README。

QQ 默认关闭。需要运行网关时，先配置 `QQ_ENABLED=true`、管理员、NapCat 地址与令牌，然后前台运行 `python main.py --gateway`。本轮未登录 QQ、启动 Docker 或安装 launchd 服务。

部分旧脚本使用 `pkill`、`launchctl` 或固定容器名，会影响匹配的进程。使用前应读脚本，确认目标，并将虚拟环境路径改为实际路径。`agent/systemd/` 的 plist 是安装模板，需要替换 `__PROJECT_ROOT__` 和 `__HOME__`。

`--douyin` 仅保留兼容入口，不再提供独立抖音网关；`start_douyin.sh` 不能恢复已移除的实现。自动学习可能持续调用模型，应明确配置预算后再启用。
