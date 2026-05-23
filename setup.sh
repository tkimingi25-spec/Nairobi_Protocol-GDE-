#!/usr/bin/env bash
set -euo pipefail
echo "Installing system packages (recommended) and Python requirements..."
if [ -x "$(command -v apt)" ]; then
  sudo apt update
  sudo apt install -y python3-networkx python3-numpy || true
fi
python3 -m pip install --user -r requirements.txt || true
echo "Setup complete. If you use Pixi, run: pixi install" 
