#!/bin/bash
# GEN-DOC - Lanceur rapide
cd "$(dirname "$0")"
source venv/bin/activate
python3 main.py gui
