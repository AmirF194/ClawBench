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
#   scripts/harbor/build-runtime-image.sh --push          # also push to Docker Hub
#   IMAGE=ghcr.io/my-org/clawbench-harbor-runtime scripts/harbor/build-runtime-image.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="$ROOT/src/clawbench/runtime"
VERSION="$(grep -m1 '^version' "$ROOT/pyproject.toml" | sed -E 's/.*"([^"]+)".*/\1/')"
IMAGE="${IMAGE:-docker.io/clawbench/clawbench-harbor-runtime}"
ENGINE="${CONTAINER_ENGINE:-docker}"
PUSH=0
[ "${1:-}" = "--push" ] && PUSH=1

# Stage a build context: the runtime tree plus resume_template.json, which the
# adapter normally copies into each task's environment/harbor/ at export time
# (setup.sh -> prepare-task.py reads /app/src/harbor/resume_template.json).
CTX="$(mktemp -d)"
trap 'rm -rf "$CTX"' EXIT
cp -r "$RUNTIME/." "$CTX/"
cp "$ROOT/src/clawbench/runner/run_support/resume_template.json" "$CTX/harbor/resume_template.json"

echo "Building $IMAGE:$VERSION (engine=$ENGINE, context=$CTX)"
"$ENGINE" build \
  -f "$CTX/harbor/Dockerfile" \
  -t "$IMAGE:$VERSION" \
  -t "$IMAGE:latest" \
  "$CTX"

if [ "$PUSH" = 1 ]; then
  "$ENGINE" push "$IMAGE:$VERSION"
  "$ENGINE" push "$IMAGE:latest"
fi
echo "Done: $IMAGE:$VERSION"
