#!/usr/bin/env bash

# Shared software-development prerequisites for BuggyBot.
# The runtime libraries used by the Hardware scripts are installed too;
# see Hardware/README.md for the LiteRT virtual environment the camera
# and TFLite scripts need.

sudo apt-get update
sudo apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-picamera2 \
    python3-opencv \
    python3-numpy \
    python3-smbus \
    python3-gpiozero

git --version
python3 --version
