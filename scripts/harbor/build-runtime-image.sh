#!/usr/bin/env bash
# Build (and optionally push) the ClawBench Harbor runtime image.
#
# The image is the environment every prebuilt-mode Harbor task points at via
# [environment].docker_image. It is built from the same Dockerfile the default
# (per-task environment/) mode copies into each task, so both modes are
# byte-identical at runtime.
#
# Usage:
#   scripts/harbor/build-runtime-image.sh                 # local tag only
#   scripts/harbor/build-runtime-image.sh --push          # also push to GHCR
#   IMAGE=ghcr.io/my-org/clawbench-harbor-runtime scripts/harbor/build-runtime-image.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="$ROOT/src/clawbench/runtime"
VERSION="$(grep -m1 '^version' "$ROOT/pyproject.toml" | sed -E 's/.*"([^"]+)".*/\1/')"
IMAGE="${IMAGE:-ghcr.io/tiger-ai-lab/clawbench-harbor-runtime}"
ENGINE="${CONTAINER_ENGINE:-docker}"
PUSH=0
[ "${1:-}" = "--push" ] && PUSH=1

echo "Building $IMAGE:$VERSION (engine=$ENGINE, context=$RUNTIME)"
"$ENGINE" build \
  -f "$RUNTIME/harbor/Dockerfile" \
  -t "$IMAGE:$VERSION" \
  -t "$IMAGE:latest" \
  "$RUNTIME"

if [ "$PUSH" = 1 ]; then
  "$ENGINE" push "$IMAGE:$VERSION"
  "$ENGINE" push "$IMAGE:latest"
fi
echo "Done: $IMAGE:$VERSION"
