#!/usr/bin/env bash
# =========================================================
# Black Hole v4.3 · Codespaces 一键启动
# Xvfb + x11vnc + noVNC + pygame
# 用法：
#   chmod +x run.sh
#   ./run.sh
# 然后浏览器打开：
#   https://<codespace>-6080.app.github.dev/vnc.html
# =========================================================
set -u   # 注意：不用 set -e，避免 apt 报错中断整个脚本

# -------- 路径（脚本自身所在目录） --------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GAME_FILE="$SCRIPT_DIR/HELLO/game_blackhole_v0.4.3.py"
VNC_PORT=5900
WEB_PORT=6080
DISPLAY_NUM=:99

echo "==========================================="
echo "  Black Hole v4.3 · Codespaces Launcher"
echo "==========================================="
echo "脚本目录: $SCRIPT_DIR"
echo "游戏文件: $GAME_FILE"
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

# 中文字体兜底（如果 fonts-noto-cjk 装失败，用文泉驿或自带字体）
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
export SDL_AUDIODRIVER=dummy      # 无声音环境，屏蔽 ALSA 报错
export PYTHONUNBUFFERED=1

# -------- 4. 启动虚拟显示 + VNC + noVNC --------
echo "[4/5] 启动虚拟显示与 VNC 服务..."

# 清理旧进程（避免 :99 / 5900 / 6080 被占用）
sudo pkill -9 Xvfb       2>/dev/null || true
sudo pkill -9 x11vnc     2>/dev/null || true
sudo pkill -9 websockify 2>/dev/null || true
sudo pkill -9 fluxbox    2>/dev/null || true
sleep 1

# Xvfb 虚拟显示
Xvfb $DISPLAY_NUM -screen 0 1440x900x24 -nolisten tcp >/dev/null 2>&1 &
sleep 2

if ! xdpyinfo -display $DISPLAY_NUM >/dev/null 2>&1; then
    echo "      ⚠ Xvfb 未响应，尝试重新启动..."
    sleep 2
fi

# fluxbox 窗口管理器（可选，让桌面好看点）
fluxbox >/dev/null 2>&1 &
sleep 1

# x11vnc：把 :99 画面推出来
x11vnc -display $DISPLAY_NUM \
       -nopw -forever -shared -forever \
       -rfbport $VNC_PORT \
       -quiet -bg >/dev/null 2>&1
sleep 1

# websockify：把 VNC 转成网页
websockify --web /usr/share/novnc/ \
           $WEB_PORT localhost:$VNC_PORT \
           >/dev/null 2>&1 &
sleep 1

# 自检
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

# 检查游戏文件
if [ ! -f "$GAME_FILE" ]; then
    echo "❌ 找不到游戏文件：$GAME_FILE"
    echo "   请确认目录结构："
    echo "   $SCRIPT_DIR/"
    echo "   ├── run.sh"
    echo "   └── HELLO/"
    echo "       └── game_blackhole_v0.4.3.py"
    exit 1
fi

# 前台运行游戏（Ctrl+C 可退出）
cd "$SCRIPT_DIR"
python3 "$GAME_FILE"

# 游戏退出后清理服务
echo ""
echo "游戏已退出，清理 VNC 服务..."
sudo pkill -9 x11vnc     2>/dev/null || true
sudo pkill -9 websockify 2>/dev/null || true
sudo pkill -9 fluxbox    2>/dev/null || true
sudo pkill -9 Xvfb       2>/dev/null || true
echo "✓ 已清理"