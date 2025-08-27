#!/usr/bin/env bash
set -euo pipefail

if [ -d "/workspace/.venv" ]; then
	. /workspace/.venv/bin/activate
fi

export PYTHONUNBUFFERED=1
python /workspace/bot.py
