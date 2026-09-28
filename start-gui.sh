#!/usr/bin/env bash
set -e
echo "Installing dependencies..."
sudo apt-get update -y
sudo apt-get install -y xvfb x11vnc fluxbox websockify novnc
echo "Starting virtual display..."
Xvfb :1 -screen 0 1024x768x24 &
export DISPLAY=:1
fluxbox &
echo "Starting VNC server..."
x11vnc -display :1 -nopw -forever -shared -rfbport 5900 &
echo "Starting noVNC on port 6080..."
websockify --web=/usr/share/novnc 6080 localhost:5900 &
echo "GUI environment is ready!"
echo "Go to the Ports tab, set port 6080 to Public, and open the link."