#!/usr/bin/env bash

# Shared software-development prerequisites for BuggyBot.
# Runs on your development computer (not the Pi). The Pi setup script is
# Hardware/setup.sh.


sudo apt-get update
sudo apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-venv

git --version
python3 --version
