#!/usr/bin/env bash

# BuggyBot Pi setup script — runs on BuggyBot (the CM5), not your dev PC.
# Installs the camera, vision, I2C, and GPIO libraries needed by the
# Hardware scripts, plus the LiteRT virtual environment.


set -e

echo "[1/3] Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3-picamera2 \
    python3-opencv \
    python3-numpy \
    python3-smbus \
    python3-gpiozero

echo "[2/3] Creating LiteRT virtual environment..."
python3 -m venv --system-site-packages ~/buggybot-venv
~/buggybot-venv/bin/pip install --upgrade pip
~/buggybot-venv/bin/pip install ai-edge-litert

echo "[3/3] Done."
echo "Run the live sign demo with:"
echo '  cd ~/BuggyBot && ~/buggybot-venv/bin/python "Model Training/OpenCV/pi_sign_detection_demo.py"'
