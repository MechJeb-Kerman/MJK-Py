#!/usr/bin/env bash
# 由 install/cloud-setup.sh 生成：升级 dsh 到最新版并重启
set -u
NODE_BIN="/home/codespace/nvm/current/bin"
CLOUD_DIR="/workspaces/MJK-Py/.dsh-cloud"
export PATH="$NODE_BIN:$PATH"

echo "BEFORE:$(dsh --version 2>/dev/null || echo unknown)"
"$NODE_BIN/npm" install -g @deepseek-ai/dsh@latest >>"$HOME/dsh-update.log" 2>&1 || { echo UPDATE:FAILED; exit 1; }
echo "AFTER:$(dsh --version 2>/dev/null || echo unknown)"

# 按端口找 PID（不要用 pkill -f "dsh web"：命令自己会命中）
PID="$(ss -ltnp 2>/dev/null | grep ':3080' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)"
[ -n "$PID" ] && kill "$PID" && sleep 2
exec bash "$CLOUD_DIR/start.sh"
