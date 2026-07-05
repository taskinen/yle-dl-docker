#!/bin/bash
set -e

# Check if web UI is enabled
if [ "$ENABLE_WEB_UI" = "1" ] || [ "$ENABLE_WEB_UI" = "true" ]; then
    # Start web server (it creates its job dir and prints its own banner)
    exec python3 /app/yle-dl-web.py
else
    # Run yle-dl CLI (default behavior)
    exec yle-dl "$@"
fi
