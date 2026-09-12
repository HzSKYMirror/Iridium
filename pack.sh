#!/usr/bin/env bash
# Pack Iridium.mcdr for release. Run from repo root.
set -euo pipefail
cd "$(dirname "$0")"
rm -f Iridium.mcdr
zip -r Iridium.mcdr iridium lang mcdreforged.plugin.json LICENSE \
	-x '*__pycache__*' -x '*.pyc'
echo "Built Iridium.mcdr"
