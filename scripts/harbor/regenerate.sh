#!/usr/bin/env bash
# Regenerate the committed prebuilt-mode Harbor dataset and registry.json.
#
# Run this whenever test-cases/v2/ or the Harbor adapter changes; CI
# (.github/workflows/validate-harbor.yml) fails if the committed copy is stale.
#
# Usage: scripts/harbor/regenerate.sh [--image <ref>]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep -m1 '^version' "$ROOT/pyproject.toml" | sed -E 's/.*"([^"]+)".*/\1/')"
IMAGE="ghcr.io/tiger-ai-lab/clawbench-harbor-runtime:$VERSION"
if [ "${1:-}" = "--image" ]; then IMAGE="$2"; fi

cd "$ROOT"
uv run clawbench-harbor-adapt \
  --output-dir harbor/datasets/clawbench-v2 \
  --docker-image "$IMAGE" \
  --overwrite

uv run --with harbor==0.22.0 python scripts/harbor/build_registry.py \
  --dataset-dir harbor/datasets/clawbench-v2 \
  --name clawbench-v2 \
  --version "$VERSION" \
  --output registry.json

uv run --with harbor==0.22.0 python scripts/harbor/build_registry.py \
  --dataset-dir harbor/datasets/clawbench-v2 \
  --manifest harbor/dataset.toml

echo "Regenerated harbor/datasets/clawbench-v2 (image=$IMAGE), registry.json, harbor/dataset.toml"
