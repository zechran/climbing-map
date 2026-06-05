#!/bin/bash
# publish.sh
# Rebuilds the HTML wiki and pushes to GitHub.
# Called automatically by Claude after any wiki changes.
#
# Usage:
#   ./publish.sh "commit message"
#   ./publish.sh  (uses default message)

set -e

cd "$(dirname "$0")"

MSG="${1:-Wiki update: $(date '+%Y-%m-%d %H:%M')}"

echo "🔨 Building wiki..."
python3 build-wiki.py

echo "📦 Committing..."
git add .
git commit -m "$MSG"

echo "🚀 Pushing to GitHub..."
git push

echo "✅ Published: $MSG"
