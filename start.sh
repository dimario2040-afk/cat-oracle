#!/usr/bin/env bash
set -e

# Install Playwright browsers if missing
if [ ! -d "/opt/render/.cache/ms-playwright/chromium-1223" ]; then
    echo "Playwright browsers not found — installing..."
    python -m playwright install chromium
    echo "Done installing Playwright browsers"
else
    echo "Playwright browsers already installed"
fi

ls -la /opt/render/.cache/ms-playwright/ 2>/dev/null || true

# Start the bot
exec python bot.py
