#!/usr/bin/env bash

# Shared software-development prerequisites for BuggyBot.
# Runs on your development computer (not the Pi). The Pi setup script is
# Hardware/setup.sh.


if [[ "$(uname)" == "Darwin" ]]; then
    # macOS: Homebrew packages. XQuartz is the X server for viewing the Pi's
    # OpenCV preview window over `ssh -Y` (log out and back in after install).
    brew install git python
    brew install --cask xquartz
else
    sudo apt-get update
    sudo apt-get install -y \
        git \
        python3 \
        python3-pip \
        python3-venv
fi

git --version
python3 --version
