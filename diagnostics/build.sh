#!/usr/bin/env bash
# Optional: build a logging-only instrumented TensorFlow v2.18.1 CPU wheel.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-$ROOT/diagnostics/results}"
IMAGE="${IMAGE:-tf-tempvar-instrumented:2.18.1}"
mkdir -p "$OUT/build"
command -v docker >/dev/null || { echo 'Docker is required' >&2; exit 2; }
docker info >/dev/null 2>&1 || { echo 'Docker daemon not available' >&2; exit 2; }
echo 'TensorFlow source build; recommended: >=24 GiB RAM and >=50 GiB free disk.'
free -h || true
df -h "$ROOT" || true
export DOCKER_BUILDKIT=1
docker build --platform linux/amd64 --progress=plain \
  --build-arg BAZEL_JOBS="${BAZEL_JOBS:-4}" \
  --build-arg BAZEL_RAM_MB="${BAZEL_RAM_MB:-12288}" \
  -f "$ROOT/diagnostics/Dockerfile" -t "$IMAGE" "$ROOT" \
  2>&1 | tee "$OUT/build/build.log"
docker run --rm --platform linux/amd64 --entrypoint python "$IMAGE" \
  -c 'import tensorflow as tf, tf_keras; print("INSTRUMENTED:", tf.__version__, tf_keras.__version__)' \
  2>&1 | tee "$OUT/build/smoke.log"
