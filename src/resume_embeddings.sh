#!/usr/bin/env bash
# Rebuild or continue the v2 embeddings (after the chunker fix). Finished shards are skipped; run from anywhere.
# Vectors of texts that already existed in v1 are copied from data/index_v1, only new texts are encoded.
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8 HF_HUB_DISABLE_PROGRESS_BARS=1
PY=.venv/Scripts/python.exe
$PY -X utf8 src/24_embed.py intfloat/multilingual-e5-small articles 384 data/index_v1/emb_multilingual-e5-small_articles
$PY -X utf8 src/24_embed.py intfloat/multilingual-e5-base articles 384 data/index_v1/emb_multilingual-e5-base_articles
$PY -X utf8 src/24_embed.py BAAI/bge-m3 articles 384 data/index_v1/emb_bge-m3_articles
$PY -X utf8 src/24_embed.py intfloat/multilingual-e5-small all 384 data/index_v1/emb_multilingual-e5-small_all
