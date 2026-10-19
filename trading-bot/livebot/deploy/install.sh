#!/usr/bin/env bash
# One-shot installer for an Ubuntu VM (Oracle Cloud Free Tier). Run as the default 'ubuntu' user:
#   bash <(curl -fsSL https://raw.githubusercontent.com/rotemGgGgGg/bigbrands/claude/serene-fermi-4483ji/trading-bot/livebot/deploy/install.sh)
set -euo pipefail
sudo apt-get update -y && sudo apt-get install -y git python3 python3-venv tzdata
cd ~ && [ -d bigbrands ] || git clone -b claude/serene-fermi-4483ji https://github.com/rotemGgGgGg/bigbrands.git
cd ~/bigbrands/trading-bot/livebot
python3 -m venv .venv && .venv/bin/pip install -q requests
[ -f config.json ] || cp config.example.json config.json
sudo tee /etc/systemd/system/gapfb.service >/dev/null <<UNIT
[Unit]
Description=GapFB-NQ trading bot
After=network-online.target
[Service]
User=$USER
WorkingDirectory=$HOME/bigbrands/trading-bot/livebot
ExecStart=$HOME/bigbrands/trading-bot/livebot/.venv/bin/python bot.py
Restart=always
RestartSec=30
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
echo "Installed. Next: nano ~/bigbrands/trading-bot/livebot/config.json  (paste token + account id), then:"
echo "  cd ~/bigbrands/trading-bot/livebot && .venv/bin/python bot.py --check"
echo "  sudo systemctl enable --now gapfb && journalctl -u gapfb -f"
