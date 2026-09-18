#!/bin/sh
# Keep the radar running: restart it if it exits for any reason, with a short
# pause so a crash loop cannot spin. Logs rotate per run into radar.log.
cd "$(dirname "$0")" || exit 1
while true; do
    echo "[supervisor] starting radar at $(date '+%H:%M:%S')" >> radar.log
    python3 main.py >> radar.log 2>&1
    echo "[supervisor] radar exited ($?) at $(date '+%H:%M:%S'); restarting in 10s" >> radar.log
    sleep 10
done
