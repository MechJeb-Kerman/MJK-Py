#!/usr/bin/env bash
# =========================================================
# Black Hole · Codespaces 一键启动（自动找最新版）
# Xvfb + x11vnc + noVNC + pygame
# 用法：
#   chmod +x run.sh
#   ./run.sh
# 然后浏览器打开：
#   https://<codespace>-6080.app.github.dev/vnc.html
# =========================================================
set -u

# -------- 路径（脚本自身所在目录） --------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GAME_DIR="$SCRIPT_DIR/HELLO"
VNC_PORT=5900
WEB_PORT=6080
DISPLAY_NUM=:99

# -------- 自动查找最新版游戏文件 --------
# 匹配 game_blackhole_v*.py，按版本号排序取最新
GAME_FILE=""
if [ -d "$GAME_DIR" ]; then
    GAME_FILE="$(ls -1 "$GAME_DIR"/game_blackhole_v*.py 2>/dev/null \
                 | sort -V \
                 | tail -n1)"
fi
# 兜底：如果没有版本号文件，找任何 game_blackhole*.py
if [ -z "$GAME_FILE" ] && [ -d "$GAME_DIR" ]; then
    GAME_FILE="$(ls -1 "$GAME_DIR"/game_blackhole*.py 2>/dev/null \
                 | sort -V \
                 | tail -n1)"
fi
# 兜底 2：在脚本目录直接找
if [ -z "$GAME_FILE" ]; then
    GAME_FILE="$(ls -1 "$SCRIPT_DIR"/game_blackhole_v*.py 2>/dev/null \
                 | sort -V \
                 | tail -n1)"
fi

echo "==========================================="
echo "  Black Hole · Codespaces Launcher"
echo "==========================================="
echo "脚本目录: $SCRIPT_DIR"
if [ -n "$GAME_FILE" ]; then
    echo "游戏文件: $GAME_FILE"
    echo "版本识别: $(basename "$GAME_FILE")"
else
    echo "游戏文件: (未找到)"
fi
echo ""

# -------- 1. 系统依赖 --------
echo "[1/5] 安装系统依赖..."
sudo rm -f /etc/apt/sources.list.d/yarn.list 2>/dev/null || true

if ! command -v Xvfb >/dev/null 2>&1 \
   || ! command -v x11vnc >/dev/null 2>&1 \
   || ! command -v websockify >/dev/null 2>&1; then
    sudo apt-get update -qq || true
    sudo apt-get install -y -qq \
        xvfb x11vnc novnc websockify fluxbox \
        fonts-noto-cjk \
        libx11-6 libxext6 libxrandr2 libxcursor1 \
        libxi6 libxfixes3 libxinerama1 \
        x11-utils || true
else
    echo "      依赖已就绪，跳过安装"
fi

if ! fc-list 2>/dev/null | grep -qi "noto.*cjk"; then
    sudo apt-get install -y -qq fonts-wqy-microhei 2>/dev/null || true
fi

# -------- 2. Python 依赖 --------
echo "[2/5] 检查 pygame..."
python3 -c "import pygame" 2>/dev/null || {
    echo "      安装 pygame..."
    python3 -m pip install -U pygame -q
}

# -------- 3. 环境变量 --------
echo "[3/5] 设置环境变量..."
export DISPLAY=$DISPLAY_NUM
export SDL_AUDIODRIVER=dummy
export PYTHONUNBUFFERED=1

# -------- 4. 启动虚拟显示 + VNC + noVNC --------
echo "[4/5] 启动虚拟显示与 VNC 服务..."

sudo pkill -9 Xvfb       2>/dev/null || true
sudo pkill -9 x11vnc     2>/dev/null || true
sudo pkill -9 websockify 2>/dev/null || true
sudo pkill -9 fluxbox    2>/dev/null || true
sleep 1

Xvfb $DISPLAY_NUM -screen 0 1440x900x24 -nolisten tcp >/dev/null 2>&1 &
sleep 2

if ! xdpyinfo -display $DISPLAY_NUM >/dev/null 2>&1; then
    echo "      ⚠ Xvfb 未响应，等待..."
    sleep 2
fi

fluxbox >/dev/null 2>&1 &
sleep 1

x11vnc -display $DISPLAY_NUM \
       -nopw -forever -shared \
       -rfbport $VNC_PORT \
       -quiet -bg >/dev/null 2>&1
sleep 1

websockify --web /usr/share/novnc/ \
           $WEB_PORT localhost:$VNC_PORT \
           >/dev/null 2>&1 &
sleep 1

if curl -sf -o /dev/null "http://localhost:$WEB_PORT/vnc.html"; then
    echo "      ✓ noVNC 已启动 (HTTP 200)"
else
    echo "      ⚠ noVNC 无响应，请检查 websockify"
fi

# -------- 5. 启动游戏 --------
echo "[5/5] 启动游戏..."
echo ""
echo "==========================================="
echo "  浏览器打开端口 $WEB_PORT 的 noVNC："
echo "  https://<你的codespace名>-$WEB_PORT.app.github.dev/vnc.html"
echo ""
echo "  或者：左侧 Ports 面板 → $WEB_PORT → 地球图标"
echo "==========================================="
echo ""

if [ -z "$GAME_FILE" ] || [ ! -f "$GAME_FILE" ]; then
    echo "❌ 找不到任何 game_blackhole_v*.py"
    echo "   请在下面这些目录里放一个："
    echo "     $GAME_DIR/"
    echo "     $SCRIPT_DIR/"
    echo ""
    echo "   当前 $GAME_DIR 内容："
    ls -la "$GAME_DIR" 2>/dev/null || echo "   （目录不存在）"
    exit 1
fi

cd "$SCRIPT_DIR"
python3 "$GAME_FILE"

echo ""
echo "游戏已退出，清理 VNC 服务..."
sudo pkill -9 x11vnc     2>/dev/null || true
sudo pkill -9 websockify 2>/dev/null || true
sudo pkill -9 fluxbox    2>/dev/null || true
sudo pkill -9 Xvfb       2>/dev/null || true
echo "✓ 已清理"