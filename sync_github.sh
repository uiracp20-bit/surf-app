#!/bin/bash
# Auto-syncs the Uira Surf Dashboard to GitHub Pages whenever it changes.
# Run by launchd every 5 minutes (and called by the 6am scheduled refresh).

FOLDER="$HOME/Documents/Claude/Artifacts/uira-surf-dashboard"
HASH_FILE="$FOLDER/.last_sync_hash"
HTML_FILE="$FOLDER/index.html"
LOG_FILE="$FOLDER/.sync_log.txt"
TOKEN_FILE="$FOLDER/.github_token"

cd "$FOLDER" || exit 1

# Regenerate the mobile view from index.html so it can never drift out of sync.
# (index.html is the single source of truth; mobile.html is always derived.)
python3 build_mobile.py >> "$LOG_FILE" 2>&1

# Keep remote URL fresh with token
if [ -f "$TOKEN_FILE" ]; then
  TOKEN=$(cat "$TOKEN_FILE")
  git remote set-url origin "https://uiracp20-bit:${TOKEN}@github.com/uiracp20-bit/surf-app.git" 2>/dev/null
fi

# Get current file hash
CURRENT_HASH=$(md5 -q "$HTML_FILE" 2>/dev/null)
LAST_HASH=$(cat "$HASH_FILE" 2>/dev/null)

# Only push if file has changed
if [ "$CURRENT_HASH" != "$LAST_HASH" ]; then
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$TIMESTAMP] Change detected — syncing..." >> "$LOG_FILE"

  git add index.html mobile.html manifest.json sw.js icon.svg
  git commit -m "Auto-update — $TIMESTAMP"
  git push origin main

  if [ $? -eq 0 ]; then
    echo "$CURRENT_HASH" > "$HASH_FILE"
    echo "[$TIMESTAMP] ✅ Pushed to GitHub Pages" >> "$LOG_FILE"
  else
    echo "[$TIMESTAMP] ❌ Push failed" >> "$LOG_FILE"
  fi
fi
