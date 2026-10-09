#!/usr/bin/env bash
# 由 install/cloud-setup.sh 生成：确保 dsh 在跑 + 拉起同步守护进程，最后一行打印带 token 的地址
set -u
NODE_BIN="/home/codespace/nvm/current/bin"
CLOUD_DIR="/workspaces/MJK-Py/.dsh-cloud"
WORKSPACE_DIR="$HOME/dsh-workspace"
LOG="$HOME/dsh-web.log"
export PATH="$NODE_BIN:$PATH"

command -v dsh >/dev/null 2>&1 || { echo "STATE:NO_DSH"; exit 1; }
mkdir -p "$WORKSPACE_DIR"

if ! curl -s -o /dev/null -m 3 http://127.0.0.1:3080/; then
  (setsid nohup bash -c "cd $WORKSPACE_DIR && exec dsh web" >"$LOG" 2>&1 </dev/null &)
  for _ in $(seq 1 30); do
    curl -s -o /dev/null -m 2 http://127.0.0.1:3080/ && break
    sleep 2
  done
fi

if [ -x "$CLOUD_DIR/sync.sh" ] && ! pgrep -f "$CLOUD_DIR/sync.sh" >/dev/null 2>&1; then
  (setsid nohup bash "$CLOUD_DIR/sync.sh" --daemon >/dev/null 2>&1 </dev/null &)
fi

echo "STATE:$(curl -s -o /dev/null -w '%{http_code}' -m 3 http://127.0.0.1:3080/ || true)"
grep -a -o 'http://127.0.0.1:3080[^ ]*' "$LOG" | tail -n 1
