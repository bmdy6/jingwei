#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$PROJECT_DIR/bin/start.sh" "$@"
