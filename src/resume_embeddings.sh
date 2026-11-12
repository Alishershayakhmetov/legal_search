#!/usr/bin/env bash
# Continue the embedding run where it stopped. Finished shards are skipped; run from anywhere.
# Remaining: multilingual-e5-small over ALL passages (shards 21-85 of 85, about one hour).
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8 HF_HUB_DISABLE_PROGRESS_BARS=1
../.venv/Scripts/python.exe -X utf8 24_embed.py intfloat/multilingual-e5-small all 384
