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
IMAGE="clawbench/clawbench-harbor-runtime:$VERSION"
if [ "${1:-}" = "--image" ]; then IMAGE="$2"; fi

cd "$ROOT"
for SUITE in v2 v1; do
  uv run clawbench-harbor-adapt \
    --suite "$SUITE" \
    --output-dir "harbor/datasets/clawbench-$SUITE" \
    --docker-image "$IMAGE" \
    --overwrite

  uv run --with harbor==0.22.0 python scripts/harbor/build_registry.py \
    --dataset-dir "harbor/datasets/clawbench-$SUITE" \
    --name "clawbench-$SUITE" \
    --version "$VERSION" \
    --output registry.json

  uv run --with harbor==0.22.0 python scripts/harbor/build_registry.py \
    --dataset-dir "harbor/datasets/clawbench-$SUITE" \
    --manifest "harbor/dataset-$SUITE.toml"
done

echo "Regenerated harbor/datasets/clawbench-{v1,v2} (image=$IMAGE), registry.json, harbor/dataset-{v1,v2}.toml"
