#!/usr/bin/env bash
set -e

# ---- 系统依赖 ----
sudo apt-get update -qq
sudo apt-get install -y -qq \
  xvfb x11vnc novnc websockify fluxbox \
  fonts-noto-cjk \
  libx11-6 libxext6 libxrandr2 libxcursor1 libxi6 libxfixes3 libxinerama1

# ---- pygame ----
python3 -m pip install -U pygame

# ---- 环境变量：虚拟屏 + 哑音频 ----
export DISPLAY=:99
export SDL_AUDIODRIVER=dummy

# ---- 虚拟显示 1440x900 ----
pgrep -x Xvfb >/dev/null || (Xvfb :99 -screen 0 1440x900x24 & sleep 2)
pgrep -x fluxbox >/dev/null || (fluxbox & sleep 1)

# ---- VNC 服务 ----
pgrep -x x11vnc >/dev/null || \
  (x11vnc -display :99 -nopw -forever -shared -rfbport 5900 -quiet & sleep 1)

# ---- noVNC（浏览器入口 6080）----
pgrep -f websockify >/dev/null || \
  (websockify --web /usr/share/novnc 6080 localhost:5900 & sleep 1)

echo "==> 打开 6080 端口访问： https://<你的codespace>-6080.app.github.dev/vnc.html"
python3 HELLO/game_blackhole_v0.3.2.py