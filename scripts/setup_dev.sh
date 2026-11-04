#!/usr/bin/env bash
set -e
cp -n .env.example .env
docker compose up -d
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
echo "OK - lance : python dev.py"
