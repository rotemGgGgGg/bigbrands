#!/usr/bin/env bash
# Puts the TRADEBRIDGE web app (dashboard + 16-year Performance page, installable on the phone) on the same Oracle VM as the bot,
# with free HTTPS: a DuckDNS name + Caddy (automatic Let's Encrypt certificate). Only the owner can sign up (BRIDGE_MAX_USERS=1).
# Usage:  bash web_install.sh <your-name>.duckdns.org <duckdns-token>
set -euo pipefail
DOMAIN="$1"; TOKEN="$2"; SUB="${DOMAIN%%.duckdns.org}"
cd ~/bigbrands && git pull -q origin claude/serene-fermi-4483ji || true
cd ~/bigbrands/trading-bot/app
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
mkdir -p ~/tradebridge-data
sudo tee /etc/systemd/system/tradebridge.service >/dev/null <<UNIT
[Unit]
Description=TRADEBRIDGE web app
After=network-online.target
[Service]
User=$USER
WorkingDirectory=$HOME/bigbrands/trading-bot/app
Environment=BRIDGE_DATA=$HOME/tradebridge-data
Environment=BRIDGE_MAX_USERS=1
ExecStart=$HOME/bigbrands/trading-bot/app/.venv/bin/uvicorn bridge.cloud:create_cloud_app --factory --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
[Install]
WantedBy=multi-user.target
UNIT
# DuckDNS: point the name at this server now and every 5 minutes
echo "url=\"https://www.duckdns.org/update?domains=$SUB&token=$TOKEN&ip=\"" > ~/duckdns.conf
(crontab -l 2>/dev/null | grep -v duckdns; echo "*/5 * * * * curl -s -K $HOME/duckdns.conf -o /dev/null") | crontab -
curl -s -K ~/duckdns.conf; echo
# Caddy reverse proxy with automatic HTTPS
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl >/dev/null
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
sudo apt-get update -y >/dev/null && sudo apt-get install -y caddy >/dev/null
echo "$DOMAIN {
    reverse_proxy 127.0.0.1:8000
}" | sudo tee /etc/caddy/Caddyfile >/dev/null
# Oracle Ubuntu images block 80/443 in iptables by default
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo apt-get install -y iptables-persistent >/dev/null 2>&1 || true; sudo netfilter-persistent save || true
sudo systemctl daemon-reload && sudo systemctl enable --now tradebridge && sudo systemctl restart caddy
echo "Done. Open https://$DOMAIN on your phone → Sign up (first account = owner) → Add to Home Screen."
