#!/bin/bash
# run_automation.sh
# Runs the README updater every 24 hours (for demo simulation could be faster)

echo "Starting Automation Scheduler..."

while true; do
    echo "Running update_readme.py..."
    python -m ai_safety_radar.scripts.update_readme
    
    echo "Sleeping for 24h..."
    sleep 86400 & wait $!
done
