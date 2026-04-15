#!/bin/zsh

set -euo pipefail

ROOT="/Users/gustavboberg/develop/softwaredesign"

# Open two Terminal tabs so the backend and frontend stay visible and easy to stop.
osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$ROOT' && python3 run.py"
    do script "cd '$ROOT/frontend' && npm run dev" in front window
end tell
EOF
